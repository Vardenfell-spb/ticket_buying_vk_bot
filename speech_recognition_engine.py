# -*- coding: utf-8 -*-

# !/usr/bin/env python3
import pydub
import requests
import speech_recognition as sr

# obtain path to "english.wav" in the same folder as this script
import os


def audio_download(urls):
    urls = urls
    for url_num, url in enumerate(urls):
        mp3_file = requests.get(url)
        dir_check()
        mp3_file_path = os.path.join("audio", 'mp3', f'message{url_num}.mp3')
        with open(mp3_file_path, 'wb') as save_file:
            save_file.write(mp3_file.content)
        wav_file = pydub.AudioSegment.from_mp3(mp3_file_path)
        wav_file.export(os.path.join("audio", 'wav', f'message{url_num}.wav'), format="wav")
        os.remove(mp3_file_path)


def dir_check():
    if not os.path.exists('audio'):
        os.mkdir('audio')
    if not os.path.exists(os.path.join('audio', 'mp3')):
        os.mkdir(os.path.join('audio', 'mp3'))
    if not os.path.exists(os.path.join('audio', 'wav')):
        os.mkdir(os.path.join('audio', 'wav'))


def vk_speech_recognition(urls):
    audio_download(urls)
    path_normalized = os.path.normpath('audio')
    reply = []
    for dirpath, _, filenames in os.walk(path_normalized):
        for file in filenames:
            full_file_path = os.path.join(dirpath, file)
            recognited_message = recognition(full_file_path)
            if recognited_message:
                reply.append(recognited_message)
            os.remove(full_file_path)
    return reply


def recognition(file):
    r = sr.Recognizer()
    with sr.AudioFile(file) as source:
        audio = r.record(source)
    try:
        message = r.recognize_google(audio, language="ru-RU")
        return message
    except sr.UnknownValueError:
        print("Google Cloud Speech could not understand audio")
    except sr.RequestError as e:
        print("Could not request results from Google Cloud Speech service; {0}".format(e))
