import os
from typing import Any, Dict, List
import sys
import argparse
import requests
from bs4 import BeautifulSoup
import json
from requests.models import MissingSchema
from json2xml import json2xml
import pandas as pd

def writeToFile(file: str, data: str):
    try:
        tempFile = open(file, 'w+')
        tempFile.write(data)
        tempFile.close()
        print('The results are exported to {file} successfully'.format(file=os.path.abspath(file)))
    except FileNotFoundError as fileNotFoundError:
        print("Checkov result file \"{filename}\" not found".format(filename=fileNotFoundError.filename))
    except TypeError as typeError:
        print(typeError.args[0])

def findText(content: str, element: str, attributes: Dict) -> str:
    result = BeautifulSoup(content, 'html.parser').find(element, attributes).text
    return result

def toDictionary(list: List) -> Dict:
    d = {}
    for line in list:
        key, value = line.strip().split(':')
        d[key.strip()] = value.strip()
    return d

def getCorrectCode(content: str) -> str:
    correctCode = findText(content, 'code', {'class': 'rdmd-code lang-go theme-light'})
    return correctCode

def getErrorDescription(content: str) -> str:
    checkovID = toDictionary(findText(content, 'div', {'class': 'markdown-body'}).split('\n'))['Error']
    return checkovID

def getCheckovID(content: str) -> str:
    checkovID = toDictionary(findText(content, 'div', {'class': 'markdown-body'}).split('\n'))['Checkov Check ID']
    return checkovID

def getSeverity(content: str) -> str:
    severity = toDictionary(findText(content, 'div', {'class': 'markdown-body'}).split('\n'))['Severity']
    return severity

def getPageContent(urlPage: str) -> str:
    try:
        content = requests.get(urlPage).text
        return content
    except MissingSchema as missingSchema:
        print(missingSchema.args[0])

def getCheckInfo(urlPage: str) -> Dict:
    content = getPageContent(urlPage)
    checkInfo = {}
    checkInfo[getCheckovID(content)] = {
        'description': getErrorDescription(content),
        'severity': getSeverity(content),
        'correctCode': getCorrectCode(content)
    }
    return checkInfo

def openJsonFile(file: str):
    try:
        tempFile = open(file, 'r')
        content = json.load(tempFile)
        tempFile.close()
        return content
    except FileNotFoundError as fileNotFoundError:
        print("Checkov result file \"{filename}\" not found".format(filename=fileNotFoundError.filename))
        sys.exit(-1)
    except TypeError as typeError:
        print("Checkov result file cannot be open as the file name has improper type. Check the argument passed to the \"openJsonFile\" function")
        sys.exit(-1)

def getErrorCheckList(file: str) -> Dict:
    checkInfo = {}
    temp = {}
    try:
        data = openJsonFile(file)
        for failedCheck in data['results']['failed_checks']:
            temp[failedCheck['check_id']]={
                'check_name':       failedCheck['check_name'],
                'evaluated_keys':   '\n'.join(failedCheck['check_result']['evaluated_keys']),
                'file_path':        failedCheck['file_path'],
                'file_line_range':  failedCheck['file_line_range'],
                'resource':         failedCheck['resource'], # resource name
                'guideline':        failedCheck['guideline']
            }
            if checkInfo is None:
                checkInfo = temp
            else:
                checkInfo.update(temp)
            print("{check_id} from {src_file} processed".format(check_id=failedCheck['check_id'], src_file=file))
        return checkInfo
    except KeyError as keyError:
        print("The key \"{key}\" is not in the json file content".format(key=keyError.args[0]))

def extendErrorCheckList(errorCheckList: Dict) -> Dict:
    for errorCheckID, errorCheckDetailList in errorCheckList.items():
        guidlineDetails = getCheckInfo(errorCheckDetailList['guideline'])[errorCheckID]
        errorCheckList[errorCheckID].update(guidlineDetails)
        print("{check_id} updated".format(check_id=errorCheckID))
    return errorCheckList

def printToCliAsJson(errorCheckList: Dict):
    print(json.dumps(obj=errorCheckList, indent=4))

def exportToHtmlTable(errorCheckList: Dict, file: str):
    html_string = '''
    <html>
    <head>
    <title>Failed Checkov Checks</title>
    <meta content="text/html; charset=UTF-8" http-equiv="Content-Type"/>
    </head>
    <link rel="stylesheet" type="text/css" href="{css_path}"/>
    <body>
        {table}
    </body>
    </html>
    '''

    df = pd.DataFrame.from_dict({key : errorCheckList[key]
                                  for key in errorCheckList.keys()
                                  }, orient='index')
    pd.set_option('colheader_justify', 'center')
    df = df.replace('\n', '<br>', regex=True)
    df = df.fillna(' ')
    data = html_string.format(css_path=os.path.abspath(os.getcwd())+"/css/df_style.css", table=df.to_html(classes='mystyle',escape=False))
    writeToFile(file, data)

def exportToXml(file: str, errorCheckList: Dict):
    data = json2xml.Json2xml(errorCheckList).to_xml()
    writeToFile(file, data)
        
def exportToJson(file: str, errorCheckList: Dict):
    data = json.dumps(obj=errorCheckList, indent=4)
    writeToFile(file, data)

def main():
    if __name__ == "__main__":
        parser = argparse.ArgumentParser()
        parser.add_argument("-o", "--output", help='''returned output one of the following: cli|html|json|xml. Default: cli''', type=str)
        parser.add_argument("-s", "--source", help='''specify the source data file. Default: ./result.json''', type=str)
        parser.add_argument("-d", "--destination", help='''specify the destination data file. Default: if --output specified, ./output.<--output>''', type=str)
        args = parser.parse_args()
        
        sourceFile = "result.json" if args.source is None else args.source
        errorCheckList = extendErrorCheckList(getErrorCheckList(file=sourceFile))
        
        if args.output == "cli":
            printToCliAsJson()
        elif args.output == "html":
            destinationFile = "output."+args.output if args.source is None else args.source
            exportToHtmlTable(errorCheckList=errorCheckList, file=destinationFile)
        elif args.output == "json":
            destinationFile = "output."+args.output if args.source is None else args.source
            exportToJson(errorCheckList=errorCheckList, file=destinationFile)
        elif args.output == "xml":
            destinationFile = "output."+args.output if args.source is None else args.source
            exportToXml(file=destinationFile, errorCheckList=errorCheckList)
        else:
            printToCliAsJson(errorCheckList=errorCheckList)

main()