import os
from typing import Dict, List
import requests
from bs4 import BeautifulSoup
import json
from requests.models import MissingSchema
from json2xml import json2xml
import pandas as pd

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
        return checkInfo
    except KeyError as keyError:
        print("The key \"{key}\" is not in the json file content".format(key=keyError.args[0]))

def extendErrorCheckList(errorCheckList: Dict) -> Dict:
    for errorCheckID, errorCheckDetailList in errorCheckList.items():
        guidlineDetails = getCheckInfo(errorCheckDetailList['guideline'])[errorCheckID]
        errorCheckList[errorCheckID].update(guidlineDetails)
    return errorCheckList

def printToCliAsJson(errorCheckList: Dict):
    print(json.dumps(obj=errorCheckList, indent=4))

def exportToHtmlTable(file: str, errorCheckList: Dict):
    html_string = '''
    <html>
    <head>
    <title>Failed Checkov Checks</title>
    <meta content="text/html; charset=UTF-8" http-equiv="Content-Type"/>
    </head>
    <link rel="stylesheet" type="text/css" href="df_style.css"/>
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
    try:
        tempFile = open(file, 'w+')
        tempFile.write(html_string.format(table=df.to_html(classes='mystyle',escape=False)))
        tempFile.close()
        print('The results are exported to {file} successfully'.format(file=os.path.abspath(file)))
    except FileNotFoundError as fileNotFoundError:
        print("Checkov result file \"{filename}\" not found".format(filename=fileNotFoundError.filename))
    except TypeError as typeError:
        print(typeError.args[0])

def exportToXml(file: str, errorCheckList: Dict):
    try:
        tempFile = open(file, 'w+')
        tempFile.write(json2xml.Json2xml(errorCheckList).to_xml())
        tempFile.close()
        print('The results are exported to {file} successfully'.format(file=os.path.abspath(file)))
    except FileNotFoundError as fileNotFoundError:
        print("Checkov result file \"{filename}\" not found".format(filename=fileNotFoundError.filename))
    except TypeError as typeError:
        print(typeError.args[0])
        
def exportToJson(file: str, errorCheckList: Dict):
    try:
        tempFile = open(file, 'w+')
        json.dump(obj=errorCheckList, indent=4, fp=tempFile)
        tempFile.close()
        print('The results are exported to {file} successfully'.format(file=os.path.abspath(file)))
    except FileNotFoundError as fileNotFoundError:
        print("Checkov result file \"{filename}\" not found".format(filename=fileNotFoundError.filename))
    except TypeError as typeError:
        print(typeError.args[0])

exportToHtmlTable("table.html", extendErrorCheckList(getErrorCheckList('result.json')))