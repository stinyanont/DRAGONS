#!/usr/bin/env groovy
/*
 * Jenkins Pipeline for DRAGONS
 *
 * by Bruno C. Quint
 *
 * Required Plug-ins:
 * - Cobertura Plug-in
 *
 */

@Library('dragons_ci@master')_


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
        CONDA_ENV_FILE=".jenkins/conda_py3env_stable.yml"
        CONDA_ENV_NAME="py3stable"
    }

    stages {

        stage("Build") {

            parallel {

                stage("CentOS 7") {
                    agent{
                        label "centos7"
                    }
                    steps {
                        echo "Building on ${env.NODE_NAME}"
                        echo "Conda home = ${env.CONDA_HOME}"
                        checkout scm
//                         condaCreateEnv $CONDA_ENV_NAME $CONDA_ENV_FILE
                    }
                }

                stage("MacOs 10.11") {
                    agent {
                        label "macosx11"
                    }
                    steps {
                        echo "Building on ${env.NODE_NAME}"
                        echo "Conda home = ${env.CONDA_HOME}"
                        checkout scm
//                         condaCreateEnv $CONDA_ENV_NAME $CONDA_ENV_FILE
                    }
                }

            }
        }
        stage('Provide') {
            parallel {
                stage("linux-64") {
                    agent{
                        label "centos7"
                    }
                    steps {
                        echo "running on ${env.NODE_NAME}"
                        echo "Conda home = ${env.CONDA_HOME}"
                    }
                }
                stage("osx-64") {
                    agent {
                        label "macosx11"
                    }
                    steps {
                        echo "running on ${env.NODE_NAME}"
                        echo "build on ${env.NODE_NAME}"
                        echo "Conda home = ${env.CONDA_HOME}"
                    }
                }
            }
        }
        stage('Test') {
            parallel {
                stage("linux-64") {
                    agent{
                        label "centos7"
                    }
                    steps {
                        echo "test on ${env.NODE_NAME}"
                        echo "Conda home = ${env.CONDA_HOME}"
                        echo "pull build"
                        echo "install build"
                        echo "run tests"
                    }
                }
                stage("osx-64") {
                    agent {
                        label "macosx11"
                    }
                    steps {
                        echo "test on ${env.NODE_NAME}"
                        echo "Conda home = ${env.CONDA_HOME}"
                        echo "pull build"
                        echo "install build"
                        echo "run tests"
                    }
                }
                stage('static metrics') {
                    steps {
                        echo "run PyLint and PyDocStyle"
                    }
                }
            }
        }
        stage('Deliver') {
            parallel {
                stage('linux-64') {
                    agent{
                        label "centos7"
                    }
                    steps {
                        echo "running on ${env.NODE_NAME}"
                        echo "deploy linux-64"
                    }
                }
                stage('noarch') {
                    steps {
                        echo "running on ${env.NODE_NAME}"
                        echo "deploy noarch"
                    }
                }
                stage('osx-64') {
                    agent {
                        label "macosx11"
                    }
                    steps {
                        echo "running on ${env.NODE_NAME}"
                        echo "deploy osx-64"
                    }
                }
            }
        }
        stage('Report') {
            steps {
                echo "Report on something"
            }
        }
    }
    post {
        failure {
            echo "Send e-mail, when failed"
        }
    }
}

//        stage ("Code pull"){
//            steps{
//                checkout scm
//            }
//        }
//
//        stage ("Set up") {
//            steps {
//                sh  '''
//                    . .jenkins/download_and_install_anaconda.sh
//                    '''
//            }
//        }
//
//        stage('Static Metrics') {
//           steps {
//               echo "PEP8 style check"
//               sh  '''
//                   mkdir -p ./reports
//
//                   pylint --exit-zero --jobs=4 \
//                       astrodata gemini_instruments gempy geminidr \
//                       recipe_system > ./reports/pylint.log
//
//                   pydocstyle --add-ignore D400,D401,D205,D105,D105 \
//                        astrodata gemini_instruments gempy geminidr \
//                        recipe_system > 'reports/pydocstyle.log' || exit 0
//                   '''
//           }
//           post {
//               always {
//                   echo 'Report pyLint warnings using the warnings-ng-plugin'
//                   recordIssues enabledForFailure: true, tool: pyLint(pattern: '**/reports/pylint.log')
//                   echo 'Report pyDocStyle warnings using the warnings-ng-plugin'
//                   recordIssues enabledForFailure: true, tool: pyDocStyle(pattern: '**/reports/pydocstyle.log')
//               }
//           }
//        }



//
//        stage('Deploy') {
//            parallel {
//                stage('deploy_1') {
//                    steps {
//                        echo "deploy 1"
//                    }
//                }
//                stage('deploy_2') {
//                    steps {
//                        echo "deploy 2"
//                    }
//                }
//            }
//        }

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

