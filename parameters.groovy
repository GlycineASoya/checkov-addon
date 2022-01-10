pipeline {
    agent any
    options {
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '5'))
    }
    /*triggers {
        cron('H * * * *')
    }*/
    stages {
        stage('Read config file') {
            steps {
                script {
                    datas = readYaml (file: 'config')
                    p = datas.collect { entry ->
                        println entry.key+':'+entry.value
                        if (entry.value instanceof String) {
                            (
                            string(defaultValue: entry.value, name: entry.key)
                            )
                        } else if (entry.value instanceof Boolean) {
                            (
                            booleanParam(defaultValue: entry.value.toBoolean(), name: entry.key)
                            )
                        } else if (entry.value instanceof ArrayList) {
                            (
                            text(defaultValue: entry.value.inject { acc, val ->"$acc\n$val"}, name: entry.key)
                            )
                        }
                    }
                    properties([parameters(p)])
                }
            }
        }
        stage('Update config file') {
            steps {
                script {
                    data = ''
                    println 'Data Initalized'
                    params.each { key, value ->
                        data += key.toString() + ': '
                        if (value instanceof Boolean) {
                            data += value.toString() + '\n'
                        } else if ((value instanceof String) && (value.contains('\n') || value.contains(','))) {
                            data += '\n- ' + value.tokenize(',\n').inject { acc, val -> "$acc\n- $val"} + '\n'
                        } else {
                            data += value.toString() + '\n'
                        }
                    }
                    println data
                    writeFile(file: 'config', text: data)
                }
                script {
                    p = params.collect { key, value ->
                        println key+':'+value
                        if ((value instanceof String) && (value.contains('\n') || value.contains(','))) {
                            (
                            text(defaultValue: value.tokenize(',\n').inject { acc, val -> val=val.trim(); "$acc\n$val"}, name: key)
                            )
                        } else if (value instanceof Boolean) {
                            (
                            booleanParam(defaultValue: value, name: key)
                            )
                        } else {
                            (
                            string(defaultValue: value, name: key)
                            )
                        }
                    }
                    println p
                    properties([parameters(p)])
                }
            }
        }
    }
}