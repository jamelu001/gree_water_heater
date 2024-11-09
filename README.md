[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://github.com/hacs/integration)

# [gree_water_heater](https://github.com/jamelu001/gree_water_heater)
# HomeAssistant 格力空气能热水器

修改自https://github.com/RobHofmann/HomeAssistant-GreeClimateComponent

使用方法:

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
