[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://github.com/hacs/integration)

# [gree_water_heater](https://github.com/jamelu001/gree_water_heater)
# HomeAssistant 格力空气能热水器

修改自https://github.com/RobHofmann/HomeAssistant-GreeClimateComponent

---------------------------------------
更新
---------------------
gree_lan是config_flow配置方式

新增热水量

使用方法:

1.将gree_lan文件夹放入custom_components文件夹中

2.将greeWat删除，删除configuration.yaml中greeWat部分

3.重启HA

4.添加集成里搜索gree_lan

5.填入ip,mac,port     

重要：mac格式为abababababab不能有：和-，字母为小写
------------------------------------------

gree_lan已经将与gree通讯的代码分离
因对HA开发不熟和精力有限，对于需要gree其他设备控制的，请自行修改代码
欢迎大佬将代码改成midea_ac_lan这种可以同时添加多种设备的代码

------------------------------------------
greeWat使用方法:

1.将greeWat文件夹放入custom_components文件夹中
        
2.configuration.yaml文件添加

        
```yaml
water_heater:
  - platform: greeWat
    name: Gree WaterHeater
    host: '热水器IP'
    port: 7000
    mac: '热水器mac'
    target_temp_step: 1
```

docker需使用host网络

测试型号为：XC70-45/G4(京东款)控制器

GR_Code.txt文件是__格力+__app提取的控制代码

本代码使用到其中的_910001一部分

```
<array name="_910001">
        <item>Pow</item>               #关0 开1
        <item>AllErr</item>
        <item>Wmod</item>              #标准0 节能1 快速2
        <item>SetTemInt</item>         #设置的温度 44
        <item>SetTemDec</item>
        <item>TemUn</item>
        <item>host</item>              
        <item>name</item>
        <item>WstpSv</item>
        <item>WstpH</item>
        <item>Wstate</item>
        <item>Watpercent</item>       #热水量 140
        <item>WatTmp</item>           #水温 144
    </array>
```
