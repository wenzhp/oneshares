#!python
#coding=UTF-8
"""
Created on 2019-06-20

@author: Jokeson

本程序用于提取当天收市的20天内第一个涨停的股票
"""
import tushare as ts
import talib
import os
import time
import datetime
import traceback
import numpy as np
import pandas as pd
import pymysql
import math


#定义数据库相关函数
def initSql():
    db = pymysql.connect(host='14.116.216.67', port=62371, user='root', passwd='jokeson@wen@aaa@123456789', db='shares',
                         charset='utf8')
    cursor = db.cursor()
    return db,cursor

def mysql_execute_command(db,cursor,sqlTxt):
    cursor.execute(sqlTxt)
    db.commit()
    return cursor

def closeDb(db,cursor):
    cursor.close()
    db.close()

#定义最小二乘法，拟合线性，a为斜率
def leastSquare(x, y):
    if len(x) == 2:
        # 此时x为自然序列
        sx = 0.5 * (x[1] - x[0] + 1) * (x[1] + x[0])
        ex = sx / (x[1] - x[0] + 1)
        sx2 = ((x[1] * (x[1] + 1) * (2 * x[1] + 1))
               - (x[0] * (x[0] - 1) * (2 * x[0] - 1))) / 6
        x = np.array(range(x[0], x[1] + 1))
    else:
        sx = sum(x)
        ex = sx / len(x)
        sx2 = sum(x ** 2)

    sxy = sum(x * y)
    ey = np.mean(y)

    a = (sxy - ey * sx) / (sx2 - ex * sx)
    b = (ey * sx2 - sxy * ex) / (sx2 - ex * sx)
    return a, b

#计算标准误差
def MSE(a,b,y,n):
    x = np.array(range(n))
    y_ = a*x + b
    sd = np.sum(np.square(y_-y))
    mse = np.sqrt(sd/(n-1))
    return mse

#通过tushare获取股票信息

def getAllSharesName() :
    sf = ts.get_stock_basics()
    names = sf['name']
    codes = names.keys()
    return names



def getFirstCeiling(code,name,df):
    days = 30
    df30 = df.iloc[0:days]
    data30 = df30[df30['p_change'] > 9]   #判断最近30天内有没有涨幅超过9%
    if data30.shape[0] == 1:      #如果30日内仅有一次涨停，就是首次涨停
        date = data30.index[0]
        idx = df.index.get_loc(date)
        dfMa = df.iloc[idx:(idx+days-1)] #取涨停日期前30日计算上升下降通道
        ma5 = np.flipud(dfMa['ma5'].values)
        ma20 = np.flipud(dfMa['ma20'].values)
        xx = np.array(range(len(ma20)))
        a0, b0 = leastSquare(xx, ma5)
        a1, b1 = leastSquare(xx, ma20)

        if a0 > 0 or a1 > 0:
            data = []
            for i in range(5):
                if (idx-i) >= 0:
                    data.append(df.iloc[idx-i]['close'])
                else:
                    data.append('null')
            print(code, a0, a1, data)
            newData = [[date,code,name,data[0],data[1],data[2],data[3],data[4]]]

            return newData
    return False

def testCeilingData(startD='',endD=''):
    if startD=='':
        startD='2019-02-01'
    if endD=='':
        endD = time.strftime("%Y-%m-%d")
    fileDate = endD.split('-')[0] + endD.split('-')[1] + endD.split('-')[2]
    dfTest = ts.get_hist_data('300099', start=endD, end=endD)
    if dfTest.shape[0] > 0:
        col = ['涨停日期', '股票代码', '名称', '当日收市', '次日收市', '第三天', '第四天', '第五天']
        df_result = pd.DataFrame()
        stock_out_file = "F://datas//hehe//stockdata//" + fileDate + ".xlsx"
        shares = getAllSharesName()
        codes = list(shares.keys())
        for co in codes:
            try:
                df = ts.get_hist_data(co, start=startD, end=endD)
                newData = getFirstCeiling(co, shares[co], df)
                if newData :
                    df_result = df_result.append(newData, ignore_index=True)
                    print(df_result.shape[0])
            except:
                print(co)
                traceback.print_exc()
            time.sleep(0.3)
        df_result.columns = col
        df_result.to_excel(stock_out_file,index=False)

#判断是否第一个涨停，且为上升通道
def isFirstCeiling(df,ma1,ma2) :
    days = 20
    if (df['p_change'][0] >= 9) and (df['p_change'][1:int(days)].max() < 9):
        ma20 = df['p_change'][0:20]
        #print(df['p_change'][0:int(days)])
        xx = np.array(range(24))
        yy0 = np.array(ma1[-(1+24):-1])
        yy1 = np.array(ma2[-(1+24):-1])
        a0,b0 = leastSquare(xx, yy0)
        a1, b1 = leastSquare(xx, yy1)
        print('\n',a0,a1)
        if a0>0 or a1>0:
            return True
    return False


def getShareData(code,startDay,endDay,shares) :
    days = '20'
    par = ['5', '24', '72', '200']  # 定义移动平均线
    stockArr = []
    df=ts.get_hist_data(code,start=startDay,end=endDay)
    #提取收盘价,倒序排列
    closed = np.flipud(df['close'].values)
    #获取均线的数据，通过timeperiod参数来分别获取 5,10,20 日均线的数据。
    ma1=talib.SMA(closed,timeperiod=int(par[0]))
    ma2=talib.SMA(closed,timeperiod=int(par[1]))
    '''ma3=talib.SMA(closed,timeperiod=int(par[2]))
    ma4 = talib.SMA(closed, timeperiod=int(par[3]))
    RSI6 = talib.RSI(closed, timeperiod=6)  # RSI的天数一般是6、12、24
    RSI12 = talib.RSI(closed, timeperiod=12)  # RSI的天数一般是6、12、24
    RSI24 = talib.RSI(closed, timeperiod=24)  # RSI的天数一般是6、12、24'''
    '''df['MACD'], df['MACDsignal'], df['MACDhist'] = talib.MACD(closed,
                                                              fastperiod=12, slowperiod=26, signalperiod=9)'''
    print(code,end=',')
    if isFirstCeiling(df,ma1,ma2) :
        print('\n'+days+"天内首次涨停股票："+shares[code] + code)
        # 使用subplots 画图
        '''f, ax = plt.subplots(2, 1, figsize=(20, 12))
        plt.rcParams['savefig.dpi'] = 400  # 图片像素
        plt.rcParams['figure.dpi'] = 400  # 分辨率
        plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
        ax[0].plot(closed, label=u'收盘', linewidth=1, color='cyan')  # 通过plog函数可以很方便的绘制出每一条均线
        ax[0].plot(ma1, label='ma' + par[0], linewidth=2, color='red')
        ax[0].plot(ma2, label='ma' + par[1], linewidth=1.5, color='darkviolet')
        ax[0].plot(ma3, label='ma' + par[2], linewidth=1, color='blue')
        ax[0].plot(ma4, label='ma' + par[3], linewidth=1, color='lime')
        ax[0].grid()  # 添加网格，可有可无，只是让图像好看点
        ax[0].legend()  # 显示图形的图例
        ax[1].plot(RSI6, label='RSI6', linewidth=2, color='red')
        ax[1].plot(RSI12, label='RSI12', linewidth=2, color='blue')
        ax[1].plot(RSI24, label='RSI24', linewidth=2, color='lime')
        ax[1].legend()  # 显示图形的图例
        plt.title(shares[code] + code)  # 绘制图形的标题
        newCode = code
        fileName = 'D://stockdata/firstCeiling/' + newCode + '.png'
        plt.savefig(fileName, format='png')
        plt.close()'''
        return True
    else:
        return False

def getAllShareData(startD='2018-01-01',endD = ''):
    if endD == '':
        endD = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    stock_data_dir = "F://datas//hehe//allstockdata//"
    shares = getAllSharesName()
    codes = list(shares.keys())
    files = os.listdir(stock_data_dir)
    for co in codes:
        if (co + '.csv') not in files:
            try:
                df = ts.get_hist_data(co, start=startD, end=endD)
                df = df.reset_index()
                df['code'] = co
                df['id'] = df['code'] + '/' + df['date']
                df = df[['id', 'code', 'date', 'open', 'high', 'close', 'low', 'volume', 'price_change', 'p_change',
                         'ma5', 'ma10', 'ma20', 'v_ma5', 'v_ma10', 'v_ma20']]
                df.to_csv(stock_data_dir+co+'.csv',index=False)
                sql = """INSERT ignore INTO shares (id,code,date,open,high,close,low,volume,price_change,p_change,
                        ma5, ma10,ma20,v_ma5,v_ma10,v_ma20)
                            values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
                param = np.array(df).tolist()
                db, cursor = initSql()
                n = cursor.executemany(sql, param)  # 将新记录插入数据库
                db.commit()
                closeDb(db, cursor)
            except:
                print(co,'数据提取失败')
            time.sleep(0.3)
#通过get_today_all更新数据库,需要自己计算ma5/ma10/ma20
def updateOneDayData():
    endD = time.strftime("%Y-%m-%d")
    df = ts.get_hist_data("sh", start=endD, end=endD)
    if df.shape[0] > 0:  # 如果当天有开市就继续更新数据
        currentData = ts.get_today_all()
        codes = list(currentData['code'])
        #print(codes)
        result = []
        resultTxt = ''
        for co in codes:
            close = list(currentData[currentData['code']==co]['trade'])[0]
            volume = list(currentData[currentData['code']==co]['volume'])[0]
            open = list(currentData[currentData['code']==co]['open'])[0]
            high = list(currentData[currentData['code'] == co]['high'])[0]
            low = list(currentData[currentData['code'] == co]['low'])[0]
            changepercent = list(currentData[currentData['code'] == co]['changepercent'])[0]
            sql = "SELECT date,close,volume from shares where code='" + co + "' order by date desc  limit 19"
            db, cursor = initSql()
            cursor.execute(sql)
            result = cursor.fetchall()
            closeDb(db, cursor)
            ma5 = close
            len5 = 4
            len10 = 9
            len20 = 19
            if len(result) < 4:
                len5 = len(result)
            if len(result) < 9:
                len10 = len(result)
            if len(result) < 19:
                len20 = len(result)
            for i in range(len5):
                ma5 += result[i][1]
            ma5 = ma5/(len5+1)
            ma10 = close
            for i in range(len10):
                ma10 += result[i][1]
            ma10 = ma10 / (len10 +1)
            ma20 = close
            for i in range(len20):
                ma20 += result[i][1]
            ma20 = ma20/(len20+1)
            v_ma5 = volume/100
            for i in range(len5):
                v_ma5 += result[i][2]
            v_ma5 = v_ma5 / (len5 + 1)
            v_ma10 = volume/100
            for i in range(len10):
                v_ma5 += result[i][2]
            v_ma10 = v_ma10 /(len10+1)
            v_ma20 = volume/100
            for i in range(len20):
                v_ma20 += result[i][2]
            v_ma20 = v_ma20 / (len20+1)
            if len(result)==0:
                price_change = 0
            else:
                price_change = close - result[0][1]
            sql = """INSERT ignore INTO shares (id,code,date,open,high,close,low,volume,price_change,p_change,ma5, ma10,ma20,v_ma5,v_ma10,v_ma20)
                                        values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
            param = [co+'/'+endD,co,endD,open,high,close,low,volume/100,price_change,changepercent,ma5, ma10,ma20,v_ma5,v_ma10,v_ma20]
            #print(param,sql)
            db, cursor = initSql()
            n = cursor.execute(sql, param)  # 将新记录插入数据库
            db.commit()
            closeDb(db, cursor)

#通过get_hist_data更新数据库
def updateDayData():
    endD = time.strftime("%Y-%m-%d")
    df = ts.get_hist_data("sh", start=endD, end=endD)
    if df.shape[0] > 0:   #如果当天有开市就继续更新数据
        startD = time.strftime("%Y-%m-%d") #取当天内的数据更新
        shares = getAllSharesName()
        codes = list(shares.keys())
        for co in codes:
            try:
                df = ts.get_hist_data(co, start=startD, end=endD)
                df = df.reset_index()
                df['code'] = co
                df['id'] = df['code'] + '/' + df['date']
                df = df[['id', 'code', 'date', 'open', 'high', 'close', 'low', 'volume', 'price_change', 'p_change',
                         'ma5', 'ma10', 'ma20', 'v_ma5', 'v_ma10', 'v_ma20']]
                sql = """INSERT ignore INTO shares (id,code,date,open,high,close,low,volume,price_change,p_change,
                        ma5, ma10,ma20,v_ma5,v_ma10,v_ma20)
                            values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
                param = np.array(df).tolist()
                db, cursor = initSql()
                n = cursor.executemany(sql, param)  # 将新记录插入数据库,忽略重复的
                db.commit()
                closeDb(db, cursor)
            except:
                print(co,'数据提取失败')
            time.sleep(0.3)

def get_ma_data(code):
    db, cursor = initSql()
    sql = 'select date,open,high,close,low,volume,price_change,p_change,ma5, ma10,ma20,v_ma5,v_ma10,v_ma20 from shares where code = "' + code + '" order by date'
    cursor.execute(sql)
    result = cursor.fetchall()
    closeDb(db, cursor)
    cols = ['date', 'open', 'high', 'close', 'low', 'volume', 'price_change', 'p_change',
            'ma5', 'ma10', 'ma20', 'v_ma5', 'v_ma10', 'v_ma20']
    df = pd.DataFrame(result, columns=cols)
    return df

def get_h_data(code):
    db, cursor = initSql()
    sql = 'select date,open,high,close,low,volume,price_change,p_change,ma5, ma10,ma20,v_ma5,v_ma10,v_ma20 from shares where code = "' + code + '" order by date'
    cursor.execute(sql)
    result = cursor.fetchall()
    closeDb(db, cursor)
    cols = ['date', 'open', 'high', 'close', 'low', 'volume', 'price_change', 'p_change',
            'ma5', 'ma10', 'ma20', 'v_ma5', 'v_ma10', 'v_ma20']
    df = pd.DataFrame(result, columns=cols)
    return df

def currentShare(low=5,high=10):
    currentData = ts.get_today_all()
    codes = list(currentData[currentData['changepercent'].between(low,high) ]['code'])   #提取实时涨幅超5%的股票进行分析
    result = []
    resultArr = []
    resultTxt = ''
    buyArr = []
    for co in codes:
        #df = get_h_data(co)
        data = list(np.array(currentData[currentData['code'] == co])[0])
        vol = data[8]
        #if df.shape[0] > 30:
        if vol >0:
            #if isFirstCeilingAndUping(df):
            try:
                res,buy = get_day_ma_slope(co,data[3],d=15,vol=vol)
            except:
                res = False
                buy = ''
            if res :
                print(data)
                try:
                    resultTxt += data[0]+data[1] +'***' + buy + '***\n' +'涨幅:'+str(data[2])+',现价:'+str(data[3])+',开盘价:'+str(data[4])+',最高:'+str(data[5])+',最低:'+str(data[6])+',成交量:'+str(data[8])+',换手率:'+str(data[9])+'\n'
                except:
                    traceback.print_exc()
                result.append(data[0])
                resultArr.append(data)
                buyArr.append(buy)
    data_quotes = ts.get_realtime_quotes(result)
    text = ''
    for i in range(len(result)):
        text += resultArr[i][0]+'***' + buyArr[i] + '***\n'+resultArr[i][1]+',涨幅:'+str(resultArr[i][2])+',现价:'+str(resultArr[i][3])+',开盘价:'+str(resultArr[i][4])+',最高:'+str(resultArr[i][5])+',最低:'+str(resultArr[i][6])+',成交量:'+str(resultArr[i][8])+',换手率:'+str(resultArr[i][9])+'\n'
        text += data_quotes.iloc[i]['name'] + '买1价/量:' + data_quotes.iloc[i]['b1_p'] + '/' + data_quotes.iloc[i]['b1_v'] + '买2价/量:' + data_quotes.iloc[i]['b2_p'] + '/' + data_quotes.iloc[i]['b3_v']  + '买3价/量:' + data_quotes.iloc[i]['b3_p'] + '/' + data_quotes.iloc[i]['b3_v']+'\n'
        text += '卖1价/量:' + data_quotes.iloc[i]['a1_p'] + '/' + data_quotes.iloc[i][
            'a1_v'] + '卖2价/量:' + data_quotes.iloc[i]['a2_p'] + '/' + data_quotes.iloc[i]['a3_v'] + '卖3价/量:' + \
                data_quotes.iloc[i]['a3_p'] + '/' + data_quotes.iloc[i]['a3_v'] + '\n'
    inventory = getInventory()
    inventory_text = ''
    if inventory.shape[0] > 0:
        for i in range(inventory.shape[0]):
            co = inventory.iloc[i]['code']
            data = list(np.array(currentData[currentData['code'] == co])[0])
            b_p = data[3]
            name = data[0]+data[1]
            yl = round(b_p - inventory.iloc[i]['b_price'],1)
            inventory_text += name + '***实时盈利情况：' + str(yl) + '/' + str(round(yl/b_p*100,1)) + '%\n'
    print(text,inventory_text)
    return text,inventory_text

#获取关注存量股票信息
def getInventory():
    sql = "select code,b_price from share_inventory where status = ''"
    db, cursor = initSql()
    cursor.execute(sql)
    result = cursor.fetchall()
    closeDb(db, cursor)
    cols = ['code', 'b_price']
    df = pd.DataFrame(result, columns=cols)
    return df

#判断是否第一个涨停，且为上升通道
def isFirstCeilingAndUping(df) :
    days = 20
    ma1 = list(df['ma5'])
    ma2 = list(df['ma20'])
    if (df['p_change'][-1-int(days):-1].max() < 9):
        xx = np.array(range(24))
        yy0 = np.array(ma1[-(1+24):-1])
        yy1 = np.array(ma2[-(1+24):-1])
        a0,b0 = leastSquare(xx, yy0)
        a1, b1 = leastSquare(xx, yy1)
        print('\n',a0,a1)
        if a0>0 or a1>0:
            return True
    return False

def get_short_up_break():
    pass

#获取连续d日的n日均线斜率，找处于平台位置的股票
def get_day_ma_slope(code,current_p,d=15,vol=0):
    startDay = (datetime.datetime.now() - datetime.timedelta(days=120)).strftime('%Y-%m-%d') #取120天内的数据更新
    endDay = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    days = '20'
    par = ['5', '24', '60', '200']  # 定义移动平均线
    stockArr = []
    df = ts.get_hist_data(code, start=startDay, end=endDay)
    # 提取收盘价,倒序排列
    closed = np.flipud(df['close'].values)
    np.append(closed,[current_p])
    volume = np.flipud(df['volume'].values)
    # 获取均线的数据，通过timeperiod参数来分别获取 5,24,60 日均线的数据。
    ma0 = talib.SMA(closed, timeperiod=int(par[0]))
    ma1 = talib.SMA(closed, timeperiod=int(par[1]))
    ma2 = talib.SMA(closed, timeperiod=int(par[2]))
    macd, macdsignal, macdhist = talib.MACD(closed, fastperiod=12, slowperiod=26, signalperiod=9)  #计算MACD,结果分别为DIF,DEA,(DIF-DEA)
    if (macd[-1] > 0) and (macdsignal[-1] > 0) :
        if (macd[-1] > macdsignal[-1]) and ((macd[-2] < macdsignal[-2])):
            buy_signal = "黄金买入点"
        else:
            buy_signal = "多头行情"
    else:
        if (macd[-1] > macdsignal[-1]) and ((macd[-2] < macdsignal[-2])):
            buy_signal = "交叉突破买入点"
        else:
            buy_signal = "不建议买入"

    #计算斜率
    xx = np.array(range(d))
    yy0 = np.array(ma0[-(1 + d):-1])
    yy1 = np.array(ma1[-(1 + d):-1])
    a0, b0 = leastSquare(xx, yy0)
    a1, b1 = leastSquare(xx, yy1)
    aa0 = math.atan(a0)
    aa1 = math.atan(a1)
    if (abs(aa0) <= 0.08) and (abs(aa1) <= 0.08):  #判断5日均线及24日均线斜率
        #print(code,a0,a1)
        #v_ma0 = talib.SMA(volume, timeperiod=int(par[0]))
        #v_ma1 = talib.SMA(volume, timeperiod=int(par[1]))
        v_ma2 = talib.SMA(volume, timeperiod=int(par[2]))     #计算60日量均线
        t0 = datetime.datetime.strptime(time.strftime('%Y-%m-%d') + ' 09:30:00', "%Y-%m-%d %H:%M:%S")
        t1 = datetime.datetime.strptime(time.strftime('%Y-%m-%d')+' 15:00:00',"%Y-%m-%d %H:%M:%S")
        t = datetime.datetime.strptime(time.strftime('%Y-%m-%d %H:%M:%S'), "%Y-%m-%d %H:%M:%S")
        a = t-t0
        if vol!=0:
            v_0 = (a.seconds/((t1-t0).seconds))*vol
        else:
            v_0 = volume

        xx = np.array(range(d))
        yy0 = np.array(v_ma2[-(1 + d):-1])
        v_a0, v_b0 = leastSquare(xx, yy0)   #计算60日均量线斜率，判断是否上升趋势
        v_a0 = math.atan(v_a0)
        if (v_a0 > 0):
            if (ma0[-1] > ma1[-1]) and (ma0[-2] < ma1[-2]):
                buy_signal  += '***5日均线突破24日均线***'
                print(buy_signal)
        if ('买入点' in buy_signal) or ('5日均线' in buy_signal):
                return True,buy_signal
        else:
            return False, ''
    else:
        return False,''

#获取5日均线突破24日均线，MACD买入指标
def getAllUping():
    currentData = ts.get_today_all()
    codes = list(currentData[currentData['changepercent'].between(2, 10)]['code'])  # 提取实时涨幅超5%的股票进行分析
    result = []
    resultArr = []
    resultTxt = ''
    buyArr = []
    days = '20'
    par = ['5', '24', '60', '200']  # 定义移动平均线
    stockArr = []
    for co in codes:
        startDay = (datetime.datetime.now() - datetime.timedelta(days=120)).strftime('%Y-%m-%d')  # 取120天内的数据更新
        endDay = time.strftime('%Y-%m-%d')
        data = list(np.array(currentData[currentData['code'] == co])[0])
        df = ts.get_hist_data(co, start=startDay, end=endDay)
        # 提取收盘价,倒序排列
        closed = np.flipud(df['close'].values)
        np.append(closed, [data[3]])
        # 获取均线的数据，通过timeperiod参数来分别获取 5,24,60 日均线的数据。
        ma0 = talib.SMA(closed, timeperiod=int(par[0]))
        ma1 = talib.SMA(closed, timeperiod=int(par[1]))
        ma2 = talib.SMA(closed, timeperiod=int(par[2]))
        macd, macdsignal, macdhist = talib.MACD(closed, fastperiod=12, slowperiod=26,
                                                signalperiod=9)  # 计算MACD,结果分别为DIF,DEA,(DIF-DEA)
        if (macd[-1] > 0) and (macdsignal[-1] > 0):
            if (macd[-1] > macdsignal[-1]) and ((macd[-2] < macdsignal[-2])):
                buy_signal = "黄金买入点"
            else:
                buy_signal = "多头行情"
        else:
            if (macd[-1] > macdsignal[-1]) and ((macd[-2] < macdsignal[-2])):

                buy_signal = "关注买入点"
            else:
                buy_signal = "不建议买入"
        if (ma0[-1] > ma1[-1]) and (ma0[-2] < ma1[-2]):
                buy_signal  += '***5日均线突破24日均线***'
        try:
            if ("黄金买入点" in buy_signal) or ("5日均线" in buy_signal):
                print(co,buy_signal,data[3],closed[-2],macd[-1],macd[-2] , macdsignal[-1], macdsignal[-2])
        except:
            pass

#获取5日均线突破24日均线，MACD买入指标
def getAllPingtai(low=-2,high=2):
    currentData = ts.get_today_all()
    codes = list(currentData[currentData['changepercent'].between(low, high)]['code'])  # 提取实时涨幅超5%的股票进行分析
    names = list(currentData[currentData['changepercent'].between(low, high)]['name'])
    result = []
    resultArr = []
    resultTxt = ''
    buyArr = []
    days = '20'
    par = ['5', '24', '60', '200']  # 定义移动平均线
    stockArr = []
    for co in codes:
        try:
            startDay = (datetime.datetime.now() - datetime.timedelta(days=120)).strftime('%Y-%m-%d')  # 取120天内的数据更新
            endDay = time.strftime('%Y-%m-%d')
            data = list(np.array(currentData[currentData['code'] == co])[0])
            df = ts.get_hist_data(co, start=startDay, end=endDay)
            # 提取收盘价,倒序排列
            closed = np.flipud(df['close'].values)
            np.append(closed, [data[3]])
            # 获取均线的数据，通过timeperiod参数来分别获取 5,24,60 日均线的数据。
            ma0 = talib.SMA(closed, timeperiod=int(par[0]))
            ma1 = talib.SMA(closed, timeperiod=int(par[1]))
            ma2 = talib.SMA(closed, timeperiod=int(par[2]))
            macd, macdsignal, macdhist = talib.MACD(closed, fastperiod=12, slowperiod=26,
                                        signalperiod=9)  # 计算MACD,结果分别为DIF,DEA,(DIF-DEA)
            if ((macd[-1] > macdsignal[-1]) and (macd[-2] < macdsignal[-2])) and (macd[-1]>0 and macdsignal[-1]>0):   #
                buy_signal = "黄金买入点"
            else:
                buy_signal = "多头行情"
            # 计算斜率
            xx = np.array(range(15))
            yy0 = np.array(ma0[-(1 + 15):-1])
            yy1 = np.array(ma1[-(1 + 15):-1])
            a0, b0 = leastSquare(xx, yy0)
            a1, b1 = leastSquare(xx, yy1)
            aa0 = math.atan(a0)
            aa1 = math.atan(a1)
            sd0 = np.std(yy0)
            sd1 = np.std(yy1)
            if (abs(aa0) <= 0.08) and (abs(aa1) <= 0.08):  # 判断5日均线及24日均线斜率
                #buy_signal += '***5日均线/24日均线平缓发展***'
                if ((ma0[-1]/ma1[-1]<1) and (ma0[-1]/ma1[-1]>0.95)) and (ma0[-2]/ma1[-2]<1) and (ma0[-3]/ma1[-3]<1):
                    buy_signal += '***5日均线准备突破24日均线***'
            try:
                if ("黄金买入点" in buy_signal) and ("5日均线" in buy_signal):
                    print(co,names[codes.index(co)],buy_signal,data[3],closed[-2],sd0,sd1)
            except:
                pass
        except:
            pass