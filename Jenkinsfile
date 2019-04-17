#!/usr/bin/env groovy
pipeline {

    agent any

    triggers {
        pollSCM('H/20 * * * 1-5')
    }

    options {
        skipDefaultCheckout(true)
        buildDiscarder(logRotator(numToKeepStr: '20'))
        timestamps()
    }

    environment {
        PATH = "$JENKINS_HOME/anaconda3/bin:$PATH"
        TEST_PATH = "$WORKSPACE/DRAGONS/test_path/"
    }

    stages {

        stage ("Code pull"){
            steps{
                checkout scm
            }
        }

        stage ("Set up") {
            steps {
                sh  '''
                    .jenkins/download_and_install_anaconda.sh
                    .jenkins/download_test_data.py
                    # .jenkins/build_and_test_venv.sh
                    # .jenkins/test_env_and_install_missing_libs.sh
                    '''
            }
        }

        stage('Static code metrics') {
           steps {
               echo "PEP8 style check"
               sh  '''
                   mkdir -p ./reports

                   pylint --exit-zero --jobs=4 \
                       astrodata gemini_instruments gempy geminidr \
                       recipe_system > ./reports/pylint.log
                   '''
           }
           post {
               always {
                   echo 'Report pyLint warnings using the warnings-ng-plugin'
                   recordIssues enabledForFailure: true, tool: pyLint(pattern: '**/reports/pylint.log')
               }
           }
        }

        stage('Checking docstrings') {
            steps {
                sh  '''
                    pydocstyle --add-ignore D400,D401,D205,D105,D105 \
                        astrodata gemini_instruments gempy geminidr \
                        recipe_system > 'reports/pydocstyle.log' || exit 0
                    '''
            }
            post {
                always {
                    echo 'Report pyDocStyle warnings using the warnings-ng-plugin'
                    recordIssues enabledForFailure: true, tool: pyDocStyle(pattern: '**/reports/pydocstyle.log')
                }
            }
        }

        stage('Tests') {
            steps {
                parallel {
                    stage('py27') {
                        steps {
                            echo 'I am running py27'
                        }
                    }
                    stage('py37') {
                        steps {
                            echo 'I am running py37'
                        }
                    }
                }
            }
        }

//        stage('Unit tests') {X
//            steps {
//                sh  '''
//                    source activate ${BUILD_TAG}
//                    coverage run -m pytest --junit-xml ./reports/test_results.xml
//                    '''
//            }
//            post {
//                always {
//                    echo ' --- Publishing test results --- '
//                    junit (
//                        allowEmptyResults: true,
//                        testResults: 'reports/test_results.xml'
//                        )
//                }
//            }
//        }

//        stage('Code coverage') {
//            steps {
//                sh  '''
//                source activate ${BUILD_TAG}
//                coverage report
//                coverage xml -o ./reports/coverage.xml
//                '''
//            }
//            post {
//                always {
//                    echo ' --- Report coverage usinig Cobertura --- '
//                    step([$class: 'CoberturaPublisher',
//                        autoUpdateHealth: false,
//                        autoUpdateStability: false,
//                        coberturaReportFile: 'reports/coverage.xml',
//                        failNoReports: false,
//                        failUnhealthy: false,
//                        failUnstable: false,
//                        maxNumberOfBuilds: 10,
//                        onlyStable: false,
//                        sourceEncoding: 'ASCII',
//                        zoomCoverageChart: false])
//
//                    echo 'Report on code coverage using Code Coverage API plugin'
//                    publishCoverage adapters: [coberturaAdapter('')]
//                }
//            }
//        }
    }
    post {
        //always {
            // sh 'conda env remove --quiet --yes -n ${BUILD_TAG}'
        //}
        failure {
            echo "Send e-mail, when failed"
        }
    }
}
