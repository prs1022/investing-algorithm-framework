"""
查看保存的实盘交易数据
"""
import os
import pandas as pd
from datetime import datetime

data_dir = "examples/live_trading_data"

if not os.path.exists(data_dir):
    print(f"❌ 数据目录不存在: {data_dir}")
    print("请先运行实盘交易机器人以生成数据")
    exit()

# 获取所有 CSV 文件
csv_files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]

if not csv_files:
    print(f"❌ 没有找到数据文件在: {data_dir}")
    exit()

print(f"📁 找到 {len(csv_files)} 个数据文件\n")

# 按时间排序
csv_files.sort(reverse=True)

# 显示最近的文件
print("最近的数据文件:")
for i, filename in enumerate(csv_files[:10], 1):
    filepath = os.path.join(data_dir, filename)
    file_size = os.path.getsize(filepath) / 1024  # KB
    file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
    
    print(f"{i}. {filename}")
    print(f"   大小: {file_size:.2f} KB")
    print(f"   时间: {file_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 读取并显示数据摘要
    try:
        df = pd.read_csv(filepath, index_col=0)
        print(f"   行数: {len(df)}")
        if 'Close' in df.columns:
            print(f"   最新价格: ${df['Close'].iloc[-1]:.2f}")
        print()
    except Exception as e:
        print(f"   ⚠️  读取失败: {e}\n")

# 交互式查看
print("\n" + "="*60)
choice = input("输入文件编号查看详情 (或按 Enter 退出): ")

if choice.isdigit() and 1 <= int(choice) <= len(csv_files):
    filename = csv_files[int(choice) - 1]
    filepath = os.path.join(data_dir, filename)
    
    print(f"\n📊 查看文件: {filename}\n")
    
    df = pd.read_csv(filepath, index_col=0)
    
    print("数据概览:")
    print(df.info())
    
    print("\n前5行:")
    print(df.head())
    
    print("\n后5行:")
    print(df.tail())
    
    if 'Close' in df.columns:
        print(f"\n价格统计:")
        print(f"  最高: ${df['Close'].max():.2f}")
        print(f"  最低: ${df['Close'].min():.2f}")
        print(f"  平均: ${df['Close'].mean():.2f}")
        print(f"  最新: ${df['Close'].iloc[-1]:.2f}")
