
'''
鼠标移动调用速度测试 ok
'''
from src.utils.debug_logger import log_print
import kmNet #import kmNet模块
import time
kmNet.init('192.168.2.188','8320','24875054') #连接盒子
#下面是python调用10000次鼠标移动函数的耗时
t1=time.time()
cnt=10000
while cnt>0:
    kmNet.move(0,10)
    cnt=cnt-1
    kmNet.move(0,-10)
    cnt=cnt-1

t2=time.time()
log_print('10000次调用耗时%sms'%((t2-t1)*1000))    



'''
鼠标物理监控 ok
'''
import kmNet
import time
kmNet.init('192.168.2.188','12545','F101383B') #连接盒子
kmNet.monitor(10000)#使能键鼠监听功能
while 1:
    if kmNet.isdown_left():
        log_print('left is down')
    if kmNet.isdown_right():
        log_print("right is down")
    if kmNet.isdown_middle():
        log_print("middle is down")
    if kmNet.isdown_side1():
        log_print('side1 is down')
    if kmNet.isdown_side2():
        log_print("side2 is down")
    time.sleep(0.5)#



'''
键盘物理监控 ok
'''
import kmNet
import time
kmNet.init('192.168.2.188','12545','F101383B') #连接盒子
kmNet.monitor(10000)#使能键鼠监听功能
while 1:
    if kmNet.isdown_keyboard(4)==1:#4是键盘A键的键值
        log_print('a is down')      #a键按下
    time.sleep(0.5)#


'''
屏蔽测试 ok
'''
import kmNet
import time
kmNet.init('192.168.2.188','12545','F101383B') #连接盒子
kmNet.monitor(10000)        #使能键鼠监听功能
kmNet.mask_keyboard(4)  #屏蔽键盘A建 按下a不会有任何反应。但是能检测到A按下
while 1:
    if kmNet.isdown_keyboard(4)==1:#4是键盘A键的键值
        log_print('a is down')      #a键按下
    time.sleep(0.5)#



'''
显示图片测试 failed  ---有点问题。
'''
import kmNet
import time
kmNet.init('192.168.2.188','12545','F101383B') #连接盒子
pic=bytearray(gImage_128x80) #有问题
kmNet.lcd_picture(pic)
