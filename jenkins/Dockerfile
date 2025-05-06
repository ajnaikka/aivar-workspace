FROM jenkins/jenkins

USER root

# Install lsb-release and Docker CLI
RUN apt-get update && apt-get install -y lsb-release wget ca-certificates

# Install Docker CLI
RUN curl -fsSLo /usr/share/keyrings/docker-archive-keyring.asc \
    https://download.docker.com/linux/debian/gpg
RUN echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.asc] \
    https://download.docker.com/linux/debian $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list
RUN apt-get update && apt-get install -y docker-ce-cli

# Install Terraform
ARG TERRAFORM_VERSION=1.5.3
RUN wget https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip \
    && unzip terraform_${TERRAFORM_VERSION}_linux_amd64.zip \
    && mv terraform /usr/local/bin/ \
    && rm terraform_${TERRAFORM_VERSION}_linux_amd64.zip

# Install prerequisites
RUN apt-get update && apt-get install -y git curl unzip xz-utils zip libglu1-mesa python3-venv

# Create a virtual environment for Python packages
RUN python3 -m venv /home/jenkins/venv

# Activate the virtual environment and install Python packages
RUN /home/jenkins/venv/bin/pip install --upgrade pip
RUN /home/jenkins/venv/bin/pip install boto botocore boto3
RUN /home/jenkins/venv/bin/pip install awscli ansible

# Add Jenkins user to Docker group
RUN groupadd -g 998 docker && usermod -aG docker jenkins
RUN usermod -aG docker jenkins

# Install Jenkins plugins using jenkins-plugin-cli
USER root
RUN jenkins-plugin-cli --plugins "blueocean docker-workflow"

# Switch to Jenkins user for security
USER jenkins

# Clean up unnecessary files
# RUN rm -rf /var/lib/apt/lists/*

# Expose the Jenkins port
EXPOSE 8080
