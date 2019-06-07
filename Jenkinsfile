#!/usr/bin/env groovy
/*
 * Jenkins Pipeline for DRAGONS
 *
 * by Bruno C. Quint
 *
 * Required Plug-ins:
 * - CloudBees File Leak Detector
 * - Cobertura Plug-in
 * - Warnings NG
 */

pipeline {

    agent any

    triggers {
        pollSCM('H * * * *')  // Polls Source Code Manager every hour
    }

    options {
        skipDefaultCheckout(true)
        buildDiscarder(logRotator(numToKeepStr: '20'))
        timestamps()
    }

    environment {
        PATH = "$JENKINS_HOME/anaconda3/bin:$PATH"
        TEST_PATH = "$WORKSPACE/test_path/"
    }

    stages {

        stage ("Prepare"){

            steps{
                checkout scm
                sh '.jenkins/scripts/download_and_install_anaconda.sh'
                sh '.jenkins/scripts/create_conda_environment.sh'
                sh '.jenkins/scripts/install_missing_packages.sh'
                sh '.jenkins/scripts/install_dragons.sh'
                sh '''source activate ${BUILD_TAG}
                      python .jenkins/scripts/download_test_data.py
                      '''
                sh '.jenkins/scripts/test_environment.sh'
                sh 'rm -rf ./reports'
                sh 'mkdir -p ./reports'
            }

        }

        stage('Code Metrics') {

            steps {
                sh '.jenkins/code_metrics/pylint.sh'
                sh '.jenkins/code_metrics/pydocstring.sh'
            }
            post {
                success {
                    recordIssues(
                        enabledForFailure: true,
                        tools: [
                            pyLint(pattern: '**/reports/pylint.log'),
                            pyDocStyle(pattern: '**/reports/pydocstyle.log')
                        ]
                    )
                }
            }

        }

        stage('Unit tests') {
            steps {
                sh  '''
                    source activate ${BUILD_TAG}
                    coverage run -m pytest --junit-xml ./reports/test_results.xml
                    '''
                sh  '''
                    source activate ${BUILD_TAG}
                    python -m coverage xml -o ./reports/coverage.xml
                    '''
            }
            post {
                always {
                    junit (
                        allowEmptyResults: true,
                        testResults: 'reports/test_results.xml'
                        )
                }
            }
        }

        stage('Integration tests') {
            steps {
                echo 'No integration tests defined yet'
            }
        }

        stage('Pack and deliver') {
            steps {
                echo 'Add a step here for packing DRAGONS into a tarball'
                echo 'Make tarball available'
            }
        }

    }
    post {
        always {
            sh 'conda remove --name ${BUILD_TAG} --all --quiet --yes'
        }
    }
}
