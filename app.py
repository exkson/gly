#!/usr/bin/env python
import json
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)

import numpy as np
import cv2
import requests
from ultralytics import YOLO
from doctr.models import ocr_predictor
import pika
import pika.credentials
from pika.channel import Channel

from extractors.cip import CIPExtractor


def get_extractor(card_type: str):
    return {
        "cip": CIPExtractor,
    }.get(card_type, CIPExtractor)


def is_valid(user):
    required_keys = ["last_name", "first_name", "birth_date"]
    return all(key in user for key in required_keys)


def log(user: dict, channel: Channel):
    channel.basic_publish(exchange="", routing_key="logs", body=json.dumps(user))
    with open("logs.txt", "a") as f:
        f.write(json.dumps(user) + "\n")


def get_image_from_stream(capture):
    ret, frame = capture.read()
    return ret, frame


def main(channel: Channel, capture: cv2.VideoCapture):
    is_currently_processing = False

    segmentation_model = YOLO("yolo11n-seg.pt")
    model = model = ocr_predictor(
        det_arch="db_resnet50", reco_arch="crnn_vgg16_bn", pretrained=True
    )

    card_counter = 0
    while True:
        ret, frame = get_image_from_stream(capture)

        frame = cv2.resize(frame, (640, 480))

        if not ret:
            continue

        annotated_frame, prediction = get_card(segmentation_model, frame)
        if not is_currently_processing and prediction is not None:
            card_counter += 1

            if card_counter >= 20:
                is_currently_processing = True

                x1, y1, x2, y2 = [int(i) for i in prediction]
                card = frame[y1:y2, x1:x2]

                document = model([card])

                try:
                    ex = get_extractor("cip")(document)
                    user = ex.extract()
                except Exception as e:
                    print(e)
                else:
                    if user:
                        log(user, channel)
                is_currently_processing = False
                card_counter = 0

        cv2.imshow("frame", annotated_frame)
        cv2.waitKey(1)


def is_included_in(box1, box2):
    x1, y1, x2, y2 = box1
    x3, y3, x4, y4 = box2
    return x1 >= x3 and y1 >= y3 and x2 <= x4 and y2 <= y4


def get_card(model, frame):
    CARD_IDS = [73, 72, 67]
    PHOTO_ID = 0

    results = model(frame)
    annotated_frame = results[0].plot()
    card_box = None
    photo_box = None

    for result in results:
        for box in result.boxes:
            if box.cls.item() in CARD_IDS:
                card_box = box.xyxy[0]
            if box.cls.item() == PHOTO_ID:
                photo_box = box.xyxy[0]

            if (
                photo_box is not None
                and card_box is not None
                and is_included_in(photo_box, card_box)
            ):
                return (annotated_frame, card_box)
    return annotated_frame, None


if __name__ == "__main__":
    capture = cv2.VideoCapture("http://10.61.16.61:8080/video")

    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            "10.61.16.131",
            credentials=pika.PlainCredentials("peace", "peace"),
        )
    )
    channel = connection.channel()
    channel.queue_declare(queue="logs")

    try:
        main(channel, capture)
    except KeyboardInterrupt:
        connection.close()
        capture.release()
        cv2.destroyAllWindows()
