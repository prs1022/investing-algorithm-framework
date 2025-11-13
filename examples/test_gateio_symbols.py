"""
测试 Gate.io 支持哪些交易对
"""
import ccxt

print("🔍 测试 Gate.io 交易对支持情况\n")

try:
    exchange = ccxt.gateio()
    
    # 加载市场
    print("📥 加载市场信息...")
    markets = exchange.load_markets()
    print(f"✅ 共 {len(markets)} 个交易对\n")
    
    # 测试常见的 USDT 交易对
    test_symbols = [
        'BTC/USDT',
        'ETH/USDT',
        'SOL/USDT',
        'LTC/USDT',
        'BNB/USDT',
        'ADA/USDT',
        'DOT/USDT',
        'MATIC/USDT'
    ]
    
    print("测试常见交易对:")
    print("-" * 60)
    
    for symbol in test_symbols:
        if symbol in markets:
            market = markets[symbol]
            status = "✅ 支持"
            
            # 检查是否活跃
            if not market.get('active', True):
                status = "⚠️  已停用"
            
            # 获取最新价格
            try:
                ticker = exchange.fetch_ticker(symbol)
                price = ticker['last']
                print(f"{status} {symbol:15} 价格: ${price:,.2f}")
            except Exception as e:
                print(f"{status} {symbol:15} (无法获取价格: {str(e)[:30]})")
        else:
            print(f"❌ 不支持 {symbol}")
    
    print("\n" + "-" * 60)
    
    # 显示所有 USDT 交易对（前 20 个）
    print("\n所有 USDT 交易对（前 20 个）:")
    usdt_pairs = [s for s in markets.keys() if '/USDT' in s]
    usdt_pairs.sort()
    
    for i, symbol in enumerate(usdt_pairs[:20], 1):
        print(f"{i:2}. {symbol}")
    
    print(f"\n共 {len(usdt_pairs)} 个 USDT 交易对")
    
    # 测试 OHLCV 数据获取
    print("\n" + "=" * 60)
    print("测试 OHLCV 数据获取:")
    print("-" * 60)
    
    for symbol in ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']:
        if symbol in markets:
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, '2h', limit=5)
                print(f"✅ {symbol:15} OHLCV: {len(ohlcv)} 条数据")
            except Exception as e:
                print(f"❌ {symbol:15} 错误: {str(e)[:50]}")
    
    print("\n" + "=" * 60)
    print("✅ 测试完成")
    
except Exception as e:
    print(f"\n❌ 错误: {e}")
    import traceback
    traceback.print_exc()
