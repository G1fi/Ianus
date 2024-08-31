# About
Ianus is a telegram bot for attendance management in a group of students at FEFU.

# Install

1. Clone repository

```bash
git clone https://github.com/G1fi/Ianus.git
```

2. Start install.sh at Debian/Ubuntu systems

```bash
chmod +x install.sh
sudo ./install.sh
```

# Usage

> start & enable
```
sudo systemctl start ianus.service
sudo systemctl enable ianus.service
```

> restart
```
sudo systemctl restart ianus.service
```

> stop
```
sudo systemctl stop ianus.service
```

> check status & logs
```
sudo systemctl status ianus.service
sudo journalctl -u ianus.service
```

# Contributing
Any suggestions on adding, improving, refactoring code and fixing security problems are welcome.
