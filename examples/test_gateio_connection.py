"""
测试 Gate.io 连接和数据获取
"""
from dotenv import load_dotenv
import ccxt

load_dotenv()

# 测试 Gate.io 连接
print("Testing Gate.io connection...")

try:
    exchange = ccxt.gateio()
    
    # 测试获取 BTC/USDT 行情
    print("\n1. Testing BTC/USDT ticker...")
    ticker = exchange.fetch_ticker('BTC/USDT')
    print(f"   ✅ BTC/USDT: ${ticker['last']:.2f}")
    
    # 测试获取 ETH/USDT 行情
    print("\n2. Testing ETH/USDT ticker...")
    ticker = exchange.fetch_ticker('ETH/USDT')
    print(f"   ✅ ETH/USDT: ${ticker['last']:.2f}")
    
    # 测试获取 OHLCV 数据
    print("\n3. Testing OHLCV data...")
    ohlcv = exchange.fetch_ohlcv('BTC/USDT', '2h', limit=5)
    print(f"   ✅ Got {len(ohlcv)} candles")
    print(f"   Latest close: ${ohlcv[-1][4]:.2f}")
    
    print("\n✅ All tests passed! Gate.io connection is working.")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\nPlease check:")
    print("1. Internet connection")
    print("2. Gate.io API is accessible")
    print("3. Symbol names are correct")
