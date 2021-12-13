# checkov-addon

## Overview

The addon doing post processing for the Checkov output file.

## Area of using

Jenkins automation

## Source and output

Source file is JSON, output is CLI (default), JSON, XML, HTML file.

## What does it do

The addon takes the necessary fields from the Checkov output and add to these key/values additional information from the Checkov guidline page for each failed check.

## Use cases

Run checkov against `.tf` files as it's written [here](https://www.checkov.io/4.Integrations/Jenkins.html).

* `python3 addon.py` - output to CLI. Source file is `./result.json`
* `python3 addon.py -o html` - the result is prepared in HTML table format, output file `./output.html`, source file `./result.json`
* `python3 addon.py --source source/source.json --output json --destination destination/destination.json` - the result is prepared in HTML table format, output file `./destination/destination.json`, source file `./source/source.json`, output file format is `json`
