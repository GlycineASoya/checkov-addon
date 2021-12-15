#!/bin/bash

checkov --directory terraform --quiet --framework=terraform -o json > results/checkov/result.json || true
python3 addon.py --source results/checkov --output html --destination results/html/result.html