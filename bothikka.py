import paramiko
import random
import string
import re
import time
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.utils import executor

API_TOKEN = '7337885470:AAHEg365mXUaYTm0zlqWuKt_hCNUcd0kaj8'
SERVER_IP = '138.2.146.97'
SERVER_USER = 'ubuntu'
SSH_KEY_PATH = r'C:\Users\iwilldie\Downloads\ssh-key.pem'

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

def random_username(prefix="hikka_"):
    return prefix + ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))

def create_user_and_install(username):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_IP, username=SERVER_USER, key_filename=SSH_KEY_PATH)

    setup_commands = f"""
    sudo useradd -m -s /usr/sbin/nologin {username}
    sudo -u {username} git clone https://github.com/hikariatama/Hikka.git /home/{username}/hikka
    sudo chown -R {username}:{username} /home/{username}/hikka
    sudo -u {username} bash -c 'cd /home/{username}/hikka && python3 -m pip install --user -r requirements.txt'
    """

    stdin, stdout, stderr = ssh.exec_command(setup_commands)
    result = stdout.read().decode() + stderr.read().decode()

    service_name = f"hikka-{username}"
    service_file = f"/etc/systemd/system/{service_name}.service"
    service_content = f"""[Unit]
Description=Hikka Userbot for {username}
After=network.target

[Service]
Type=simple
User={username}
WorkingDirectory=/home/{username}/hikka
ExecStart=/usr/bin/python3 -m Hikka
StandardOutput=append:/home/{username}/hikka.log
StandardError=append:/home/{username}/hikka.log
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""

    create_service_cmd = f"""
    echo '{service_content}' | sudo tee {service_file} > /dev/null
    sudo systemctl daemon-reexec
    sudo systemctl daemon-reload
    sudo systemctl enable {service_name}
    sudo systemctl start {service_name}
    """

    stdin2, stdout2, stderr2 = ssh.exec_command(create_service_cmd)
    result += stdout2.read().decode() + stderr2.read().decode()

    ssh.close()
    return result

def find_login_link(ssh, username, timeout=60):
    log_path = f"/home/{username}/hikka.log"
    pattern = r'(tg://login\?token=[^\s]+)'
    for _ in range(timeout):
        stdin, stdout, stderr = ssh.exec_command(f"cat {log_path}")
        output = stdout.read().decode()
        match = re.search(pattern, output)
        if match:
            return match.group(1)
        time.sleep(1)
    return None

@dp.message_handler(commands=['create_hikka'])
async def handle_create_hikka(message: Message):
    username = random_username()
    await message.answer(f"🔧 Создаю Hikka-юзербота под пользователем `{username}`...")
    
    try:
        result = create_user_and_install(username)
        await message.answer("✅ Установка завершена. Ожидаю ссылку авторизации...")

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_IP, username=SERVER_USER, key_filename=SSH_KEY_PATH)

        login_link = find_login_link(ssh, username)
        ssh.close()

        if login_link:
            await message.answer(f"🚪 Ваша ссылка авторизации:\n[Нажмите для входа]({login_link})", parse_mode="Markdown")
        else:
            await message.answer("⚠️ Ссылка авторизации не найдена за 60 секунд. Попробуйте позже или проверьте логи.")
    except Exception as e:
        await message.answer(f"❌ Ошибка:\n```\n{e}\n```", parse_mode="Markdown")

if __name__ == '__main__':
    executor.start_polling(dp)