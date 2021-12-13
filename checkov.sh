#!/bin/bash

checkov --directory . --quiet --framework=terraform -o json > result.json || true
python3 addon.py