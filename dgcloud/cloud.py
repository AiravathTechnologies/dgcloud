import paramiko


class ServerManager:
    def __init__(self, server_ip, ssh_user, ssh_password):
        self.server_ip = server_ip
        self.ssh_user = ssh_user
        self.ssh_password = ssh_password
        self.ssh_connect_start()

    def ssh_connect_start(self):
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        self.ssh.connect(
            self.server_ip,
            port=22,
            username=self.ssh_user,
            password=self.ssh_password,
        )

    def ssh_connect_close(self):
        self.ssh.close()

    def ssh_execute_command(self, command, port=22):
        stdin, stdout, stderr = self.ssh.exec_command(command)
        stdout = stdout.read().decode().strip()
        stderr = stderr.read().decode().strip()
        return stdout, stderr

    def check_git_access(self):
        out, error = self.ssh_execute_command("ssh -T git@github.com")
        if "denied" in error:
            print(f"Git access denied for user {self.ssh_user}")
            return False
        return True

    def git_pull(self, git_repo_path):
        if self.check_git_access():
            STATUS, COMMANDS = self.git_changes(git_repo_path)
            command = f"cd {git_repo_path} && git pull"
            out, error = self.ssh_execute_command(command)
            if STATUS:
                for command in COMMANDS:
                    out, error = self.ssh_execute_command(command)
                    print("commands executin : ",out,error)
                    if error:
                        print(f"Error running command: {command}")
                        return None
            return out
        return None

    def git_application_status(self, service):
        service = f"echo '{self.ssh_password}' |  sudo -S systemctl status {service} | grep 'Active' "
        service_status_data, service_stderr = self.ssh_execute_command(service)
        service_status = (
            service_status_data.strip().split("since")[0].split("Active: ")[-1]
        )
        return service_status

    def restart_application(self, socket, service):
        command = f"echo '{self.ssh_password}' | sudo -S systemctl restart {socket} && echo '{self.ssh_password}' | sudo -S systemctl restart {service}"
        out, error = self.ssh_execute_command(command)
        return out

    def git_changes(self, git_repo_path):
        check_files_command = (
            f"cd {git_repo_path} && git diff --name-only HEAD..origin/main"
        )
        out, error = self.ssh_execute_command(check_files_command)
        if error:
            return None

        watched_files = {
            "models.py": "python manage.py makemigrations && python manage.py migrate",
            "requirements.txt": "pip install -r requirements.txt",
        }

        changed_files = out.strip().split("\n")
        commands_to_run = [
            watched_files[file] for file in watched_files if file in changed_files
        ]

        return True if len(commands_to_run) > 0 else False, commands_to_run


    def udpate_applicaiton(self,data):
        command = f'''
                    echo "{self.ssh_password}" | sudo -S chmod -R 777 /web 
                    cd {data["git_repo_path"]}
                    git stash
                    git pull
                    sudo systemctl restart {data['socket_name']} && sudo systemctl restart {data['service_name']} && sudo systemctl status {data['socket_name']} {data['service_name']}
                    '''
        out, error = self.ssh_execute_command(command)
        return out
