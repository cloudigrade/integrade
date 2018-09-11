node_label = 'f27'
pipeline {
  agent {
    label node_label
  }
  stages {
    stage('Run Gitlab Pipeline and Process Results') {
      steps {
        script {
          stage('Clone Project') {
              checkout([$class: 'GitSCM', branches: [[name: '*/master']], doGenerateSubmoduleConfigurations: false, extensions: [], submoduleCfg: [], userRemoteConfigs: [[url: 'https://gitlab.com/cloudigrade/integrade.git']]])
              node_name = NODE_NAME
              echo "NODE_NAME: $NODE_NAME"
		} // Clone Project
          stage('Run GitLab Pipeline') {
              withPythonEnv('System-CPython-3.6') {
	          withCredentials([[$class: 'StringBinding', credentialsId: 'dd99752e-b70e-4090-a221-d97b76f2e9a2', variable: 'GITLAB_API_TOKEN']]){
                echo "NODE_NAME: $NODE_NAME"
		pysh 'echo $PWD'
                pysh 'python --version'
                pysh 'ls -al'
                pysh 'pip install -r .jenkins-requirements.txt'
                pysh 'PIPELINE_BRANCH_NAME=master PROJECT_ID=7449621 DEPLOY_JOB_NAME="Deploy Cloudigrade" python scripts/run_pipeline_and_get_artifacts.py'
                junit allowEmptyResults: true, testResults: '*.xml'
                archiveArtifacts allowEmptyArchive: true, artifacts: '*.log'
                pysh 'make clean'
              } // withCredentials
          } // withPythonEnv
        } // Run GitLab Pipeline
    } // scripts
    } // steps
    } // Run GitLab Pipeline and Process Results
  } // stages
  post {
    always {
      script {
        sh 'pwd'
	    sh 'ls -al'
	    sh 'rm -rf *'
	    sh 'ls -al'
     } // script
    } // always
   } // post
} // pipeline
