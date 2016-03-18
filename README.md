#这是迅雷云监工源代码
***
##说明：我只是搬运工
***
***   

- 端口：4000
- 第一次获得密码方法，端口后加/install

***    
##2016.03.09 更新
***
更新user.py，解决登出其他用户直接到login页面问题
***
##2016.03.08 更新
***
感谢Dream.Fei的源代码  
更新开宝箱功能，说明进入crysadm文件夹看     

更改收水晶时间为6小时，迅雷帐号最大为200
***
##2016.03.04 14:30 更新
***
更新cron.sh脚本，实现每小时重启一次监工，分钟时间是随机一次
***
##2016.03.02 17:00 更新
***
更新README.MD文件
***
##2016.03.02 9:40更新
***
源代码降回提现功能版本<br>
开宝箱版有问题<br>
刷新数据改为15秒更新<br>
***
##2016.03.01 17:00更新
***
升级了开免费宝箱功能<br>
收水晶改为6小时收一次<br>
***
##以前更新
***
此版本增加了自动提现功能<br>
此版本加了环境安装脚本，安装脚本支持ubuntu 14.04，debian 8，kali 2.0，实测可用<br>
***
##用法
进入系统后先升级源，输入命令<br>
    `sudo apt-get update` <br>
等一会自动下载，输入命令 <br>
`sudo apt-get install -y git` <br>
如果出现`bash: sudo: command not found`错误，说明没有安装这个程序，直接输入命令<br>
`apt-get install -y sudo git`<br>
用 `cd` 命令进入任意可写权限文件夹，输入命令<br>
`sudo git clone https://github.com/sanzuwu/crysadm.git`<br>
等待下载完成，输入命令<br>
`cd crysadm  && sudo chmod +x setup.sh && ./setup.sh`<br>
此时等待安装，完成后会自动启动云监工。<br>
***
##PS:<br>
***
run.sh是运行脚本，down.sh是停止脚本，setup.sh是安装环境脚本。<br>
***
剩下的就是设置自启动，隔一段时间自动重启程序，还有时区设置问题，自行百度。<br>
***
#联系方式<br>
***
EMail:(sanzuwu@gmail.com)
***
