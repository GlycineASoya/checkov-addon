from collections import OrderedDict
import os
from typing import Any, Dict, List
import sys
import argparse
import requests
from bs4 import BeautifulSoup, NavigableString, Tag
import json
from pathlib import Path
from requests.models import MissingSchema
from json2xml import json2xml
import pandas as pd
import re
import uuid
from pathlib import Path

def getRepoLink() -> str:
    try:
        return requests.get(os.environ['TERRAFORMREPO']).url
    except:
        return ''

def writeToFile(file: str, data: str):
    try:
        Path(os.path.dirname(file)).mkdir(parents=True, exist_ok=True)
        tempFile = open(file, 'w+')
        tempFile.write(data)
        tempFile.close()
        print('The results are exported to {file} successfully'.format(file=os.path.abspath(file)))
    except FileNotFoundError as fileNotFoundError:
        print("Checkov output file \"{filename}\" cannot be created".format(filename=fileNotFoundError.filename))
    except TypeError as typeError:
        print(typeError.args[0])

def findText(content: str, element: str, attributes: Dict):
    result = BeautifulSoup(content, 'html.parser').find(element, attributes).text
    return result

def findAll(content: str, element: str):
    result = BeautifulSoup(content, 'html.parser').find_all(element)
    return result

def toDictionary(list: List) -> Dict:
    d = {}
    for line in list:
        key, value = line.strip().split(':')
        d[key.strip()] = value.strip()
    return d

def getFixValue(nextNode) -> str:
    value = ''
    label = '''<div><input class="spoilercheck" type="checkbox" id="spoilercheck{uuid}"><label for="spoilercheck{uuid}" class="spoilerlabel">{text}</label>'''
    div = '''<div class="spoilerdiv"><p>{text}</p></div></div>'''
    counter = 0
    isNext = False
    
    while nextNode is not None and nextNode.name != 'h1':
        temp = ''
        nextNode = nextNode.nextSibling
        while nextNode is not None and nextNode.name != 'h2' and nextNode.name != 'h1':
            if isinstance(nextNode, Tag):
                if nextNode.name == 'div':
                    temp = temp + next(iter([str(content) for content in nextNode.contents for contentClass in content['class'] if 'inner' in contentClass]))
                else:
                    temp = temp + str(nextNode)
                    isNext = True
            nextNode = nextNode.nextSibling
        if nextNode is not None and nextNode.name == 'h2':
            if isNext: value = value + div.format(text=temp)
            counter += 1
            value = value + label.format(uuid=uuid.uuid4(), text=nextNode.text)
            isNext = False
        else:
            value = value + div.format(text=temp)
        value = re.sub('\<button.*?\/button\>', '', value)
    return value

def getFixTextValue(nextNode) -> str:
    value = ''
    while nextNode is not None and nextNode.name != 'h1':
        if isinstance(nextNode, Tag) and nextNode.text != '':
            if nextNode.name == 'div':
                value = value + next(iter([content.text for content in nextNode.contents for contentClass in content['class'] if 'inner' in contentClass])) + '\n'
            else:
                value = value + nextNode.text + '\n'
        nextNode = nextNode.nextSibling
    return value

def getFixRuntime(content) -> str:
    correctCode = ''
    for header in content:
        nextNode = header
        if nextNode.name == 'h1' and re.compile('Fix.{1,3}R.{1,2}time').match(nextNode.text):
            correctCode = getFixValue(nextNode = nextNode.nextSibling)
    return correctCode

def getFixBuildtime(content) -> str:
    correctCode = ''
    for header in content:
        nextNode = header
        if nextNode.name == 'h1' and re.compile('Fix.{1,3}B.{1,4}time').match(nextNode.text):
            correctCode = getFixValue(nextNode = nextNode.nextSibling)
    return correctCode

def getErrorDescription(content: str) -> str:
    contentDict = toDictionary(content.split('\n'))
    errorDescription = contentDict['Error'] if 'Error' in contentDict.keys() else ''
    return errorDescription

def getCheckovID(content: str) -> str:
    contentDict = toDictionary(content.split('\n'))
    checkovID = contentDict['Checkov Check ID'] if 'Checkov Check ID' in contentDict.keys() else ''
    return checkovID

def getSeverity(content: str) -> str:
    contentDict = toDictionary(content.split('\n'))
    severity = contentDict['Severity'] if 'Severity' in contentDict.keys() else ''
    return severity
    
def getPrismaCloudSeverity(content: str) -> str:
    contentDict = toDictionary(content.split('\n'))
    prismaCloudSeverity = contentDict['Prisma Cloud Severity'] if 'Prisma Cloud Severity' in contentDict.keys() else ''
    return prismaCloudSeverity

def getBridgecrewSeverity(content: str) -> str:
    contentDict = toDictionary(content.split('\n'))
    bridgecrewSeverity = contentDict['Bridgecrew Severity'] if 'Bridgecrew Severity' in contentDict.keys() else ''
    return bridgecrewSeverity

def getPageContent(urlPage: str) -> str:
    try:
        content = requests.get(urlPage).text
        return content
    except MissingSchema as missingSchema:
        print(missingSchema.args[0])

def getGuidelineInfo(urlPage: str) -> Dict:
    content = getPageContent(urlPage)
    introductionContent = findText(content, 'div', {'class': 'markdown-body'})
    fixContent = findAll(content, 'h1')
    guidelineInfo = {}
    guidelineInfo = {
        'description': getErrorDescription(introductionContent),
        'severity': getSeverity(introductionContent) if getSeverity(introductionContent) != '' else (getPrismaCloudSeverity(introductionContent) if getPrismaCloudSeverity(introductionContent) != '' else getBridgecrewSeverity(introductionContent)),
        'fixRuntime': getFixRuntime(fixContent),
        'fixBuiltime': getFixBuildtime(fixContent)
    }
    return guidelineInfo

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

def reorderDict(dictionary: Dict, keyOrder: List) -> Dict:
    orderedDict = OrderedDict(dictionary)
    for key in keyOrder:
        orderedDict.move_to_end(key)
    return orderedDict

def getErrorCheckList(file: str) -> Dict:
    checkInfo = {}
    temp = {}
    try:
        data = openJsonFile(file)
        for failedCheck in data['results']['failed_checks']:
            temp[(failedCheck['check_id'],failedCheck['resource'])]={
                'file':         '{file_path}#{file_line}'.format(
                                    file_path = failedCheck['file_path'],
                                    file_line = str(failedCheck['file_line_range'][0])),
                'resource':     failedCheck['resource'], # resource name
                'guideline':    failedCheck['guideline']
            }
            if checkInfo is None:
                checkInfo = temp
            else:
                checkInfo.update(temp)
            print("{check_id} for {resource} from {src_file} processed".format(check_id=failedCheck['check_id'], resource=failedCheck['resource'], src_file=file))
        return checkInfo
    except KeyError as keyError:
        print("The key \"{key}\" is not in the json file content".format(key=keyError.args[0]))

def extendErrorCheckList(errorCheckList: Dict) -> Dict:
    for errorCheckID, errorCheckDetailList in errorCheckList.items():
        if errorCheckDetailList['guideline'] is None:
            print("{check_id} doesn't have guideline".format(check_id=errorCheckID))
        else:
            guidlineDetails = getGuidelineInfo(errorCheckDetailList['guideline'])
            errorCheckList[errorCheckID].update(guidlineDetails)
            keyOrder = ['severity', 'description', 'file', 'resource', 'fixBuiltime', 'fixRuntime', 'guideline']
            errorCheckList[errorCheckID] = reorderDict(errorCheckList[errorCheckID], keyOrder)
            print("{check_id} updated".format(check_id=errorCheckID))
    return errorCheckList

def insertHtmlTags(errorCheckList: Dict) -> Dict:
    repoLink = getRepoLink()
    try:
        for errorCheckID, errorCheckDetailList in errorCheckList.items():
            for errorCheckDetailKey, errorCheckDetailValue in errorCheckDetailList.items():
                if errorCheckDetailKey == 'file':
                    if repoLink != '':
                        errorCheckList[errorCheckID][errorCheckDetailKey] = '<a href=\"{repo_link}{file_path_line}\" target=\"_blank\">{file_path}</a>'.format(
                            repo_link = '{protocol}//{server}/projects/{project}/repos/{repo}/browse'.format(
                                protocol=repoLink.split('/')[0],
                                server=repoLink.split('/')[-4],
                                project=repoLink.split('/')[-2],
                                repo=repoLink.split('/')[-1].split('.')[0]),
                            file_path_line = errorCheckDetailValue,
                            file_path = errorCheckDetailValue.split('#')[0])
                if errorCheckDetailKey == 'guideline' and errorCheckDetailValue != None:
                    errorCheckList[errorCheckID][errorCheckDetailKey] = '<a href=\"{url}\" target=\"_blank\">link</a>'.format(
                        url=errorCheckDetailValue)
    except:
        print('INSERTING HTML TAGS FAILED')
    return errorCheckList

def removeHtmlTags(errorCheckList: Dict) -> Dict:
    try:
        temp = {}
        label = value = ''
        for errorCheckID, errorCheckDetailList in errorCheckList.items():
            for errorCheckDetailKey, errorCheckDetailValue in errorCheckDetailList.items():
                if errorCheckDetailKey == 'fixBuiltime' or errorCheckDetailKey == 'fixRuntime':
                    for nextNode in BeautifulSoup(errorCheckDetailValue, 'html.parser'):
                        if nextNode.name == 'label':
                            label = nextNode.text
                            value = ''
                        if nextNode.name == 'div':
                            value = nextNode.text
                        if label != '' and value != '':
                            temp[label] = value
                            errorCheckList[errorCheckID][errorCheckDetailKey] = temp
                temp = {}
    except:
        print('REMOVING HTML TAGS FAILED')
    return errorCheckList

def printToCliAsJson(errorCheckList: Dict):
    errorCheckList = removeHtmlTags(errorCheckList)
    print(json.dumps(obj=errorCheckList, indent=4))

def exportToHtmlTable(errorCheckList: Dict, file: str):
    main_props = [
        ('font-size', '10pt'),
        ('font-family', 'Arial'),
        ('border-collapse', 'collapse'),
        ('table-layout', 'auto'),
        ('width', '100%'),
        ('white-space', 'pre-line')
    ]
    
    tr_hover_props = [
        ('cursor', 'text')
    ]
    
    th_td_props = [
        ('border-collapse', 'collapse'), 
        ('border', '1px solid black'),
        ('padding', '5px')
    ]
    
    spoilercheck_props = [
        ('visibility', 'hidden'),
        ('display', 'none')
    ]
    
    spoilerlabel_props = [
        ('color', 'blue'),
        ('font-size', '1em'),
        ('cursor', 'pointer'),
        ('font-weight', 'bold')
    ]

    spoilerlabel_hover_props = [
        ('background-color', 'lightgray')
    ]
    
    spoilerdiv_props = [
        ('background-color', 'lightgray'),
        ('padding', '1px'),
        ('height', '0'),
        ('font-size', '0'),
        ('margin-top', '10px'),
        ('transition', '500ms'),
        ('opacity', '0'),
        ('border-radius', '15px')
    ]

    spoilercheck_checked_spoilerdiv_props = [
        ('height', 'auto'),
        ('font-size', '1em'),
        ('opacity', '1')
    ]
    
    spoilercheck_checked_spoilerlabel_props = [
        ('color', 'black'),
        ('font-weight', 'normal')
    ]
    
    styles = [
        dict(selector='', props=main_props),
        dict(selector='.spoilercheck', props=spoilercheck_props),
        dict(selector='.spoilerlabel', props=spoilerlabel_props),
        dict(selector='.spoilerlabel:hover', props=spoilerlabel_hover_props),
        dict(selector='.spoilerdiv', props=spoilerdiv_props),
        dict(selector='.spoilercheck:checked ~ .spoilerdiv', props=spoilercheck_checked_spoilerdiv_props),
        dict(selector='.spoilercheck:checked ~ .spoilerlabel', props=spoilercheck_checked_spoilerlabel_props),
        dict(selector='th', props=th_td_props),
        dict(selector='td', props=th_td_props),
        dict(selector='tr:hover', props=tr_hover_props)
    ]
    
    errorCheckList = insertHtmlTags(errorCheckList)
    
    df = pd.DataFrame.from_dict({key : errorCheckList[key]
                                  for key in errorCheckList.keys()
                                  }, orient='index')
    pd.set_option('colheader_justify', 'center')
    df['severity'] = pd.Categorical(df['severity'], categories=['HIGH', 'MEDIUM', 'LOW'], ordered=True)
    df['severity'] = df['severity'].cat.add_categories('None')
    df = df.sort_values(by='severity', ascending=True, na_position='last')
    df = df.droplevel(level=[1])
    df = df.fillna('None')
    data = '<link rel="stylesheet" type="text/css" href="{css_path}"/><body>{table}</body>'.format(css_path=os.path.abspath(os.getcwd()+"/css/style.css"), table=df.replace('\n', '<br>', regex=True).to_html(classes='mystyle', escape=False)) if Path(os.path.abspath(os.getcwd())+"/css/style.css").exists() else df.style.set_table_styles(styles).to_html()
    writeToFile(file, data)

def exportToXml(errorCheckList: Dict, file: str):
    errorCheckList = removeHtmlTags(errorCheckList)
    data = json2xml.Json2xml(errorCheckList).to_xml()
    writeToFile(file, data)

def exportToJson(errorCheckList: Dict, file: str):
    errorCheckList = removeHtmlTags(errorCheckList)
    data = json.dumps(obj=errorCheckList, indent=4)
    writeToFile(file, data)

def main():
    if __name__ == "__main__":
        parser = argparse.ArgumentParser()
        parser.add_argument("-o", "--output", help='''returned output one of the following: cli|html|json|xml. Default: cli''', type=str)
        parser.add_argument("-s", "--source", help='''specify the source data file. Default: ./result.json''', type=str)
        parser.add_argument("-d", "--destination", help='''specify the destination data file. Default: if --output specified, ./output.<--output>''', type=str)
        args = parser.parse_args()
        
        sourceFile = "result.json" if args.source is None else (args.source if os.path.isabs(args.source) else os.getcwd()+'/'+args.source)
        errorCheckList = extendErrorCheckList(getErrorCheckList(file=sourceFile))
        
        if args.output == "cli":
            printToCliAsJson()
        elif args.output == "html":
            destinationFile = "output."+args.output if args.destination is None else (args.destination if os.path.isabs(args.destination) else os.getcwd()+'/'+args.destination)
            exportToHtmlTable(errorCheckList=errorCheckList, file=destinationFile)
        elif args.output == "json":
            destinationFile = "output."+args.output if args.destination is None else (args.destination if os.path.isabs(args.destination) else os.getcwd()+'/'+args.destination)
            exportToJson(errorCheckList=errorCheckList, file=destinationFile)
        elif args.output == "xml":
            destinationFile = "output."+args.output if args.destination is None else (args.destination if os.path.isabs(args.destination) else os.getcwd()+'/'+args.destination)
            exportToXml(file=destinationFile, errorCheckList=errorCheckList)
        else:
            printToCliAsJson(errorCheckList=errorCheckList)

main()