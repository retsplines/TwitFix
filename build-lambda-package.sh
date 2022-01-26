#!/bin/bash
rm package.zip
cd package
zip -r ../package.zip *
cd ..
zip -g package.zip lambda_function.py
zip -g package.zip config.json
zip -g package.zip template.html

