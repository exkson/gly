#!/usr/bin/env python
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)

import cv2
from ultralytics import YOLO
from doctr.models import ocr_predictor
import pika
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
    channel.basic_publish(exchange="", routing_key="logs", body=user)


def main():
    pass


if __name__ == "__main__":
    should_run = True
    is_currently_processing = False

    segmentation_model = YOLO("yolo11n-seg.pt")
    model = ocr_predictor(pretrained=True)

    capture = cv2.VideoCapture(0)

    CARD_SLUG = "book"

    is_card_detected = False

    connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
    channel = connection.channel()
    channel.queue_declare(queue="logs")

    while should_run:
        ret, frame = capture.read()

        if not ret:
            continue

        results = segmentation_model(frame)
        annotated_frame = results[0].plot()
        for result in results:
            for box in result.boxes:
                category = segmentation_model.names.get(box.cls.item())
                if category == CARD_SLUG:
                    is_card_detected = True
                    break

        if is_card_detected and not is_currently_processing:
            document = model([frame])
            try:
                ex = get_extractor("cip")(document)
                user = ex.extract()
            except Exception as e:
                print(e)
            else:
                if user is is_valid(user):
                    log(user, channel)
                    should_run = False

        cv2.imshow("frame", annotated_frame)
        cv2.waitKey(1)
