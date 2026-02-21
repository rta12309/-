from wallet_scanner import filter_holders_by_usd, passes_behavior_rules


def test_filter_holders_by_usd_raw():
    holders = [
        {"TokenHolderAddress": "0x1", "TokenHolderQuantity": str(500_000 * 10**6)},
        {"TokenHolderAddress": "0x2", "TokenHolderQuantity": str(100_000 * 10**6)},
    ]
    out = filter_holders_by_usd(
        holders=holders,
        token_price_usd=1.0,
        min_usd=300_000,
        max_usd=30_000_000,
        decimals=6,
        holder_quantity_is_raw=True,
    )
    assert [o.address for o in out] == ["0x1"]


def test_passes_behavior_rules():
    txs = [
        {"timeStamp": "1735689600", "from": "0xa", "to": "0xwallet"},
        {"timeStamp": "1735689601", "from": "0xb", "to": "0xwallet"},
        {"timeStamp": "1735689602", "from": "0xc", "to": "0xwallet"},
        {"timeStamp": "1735689603", "from": "0xwallet", "to": "0xd"},
    ]
    ok, tx_count, inbound_ratio, unique_senders = passes_behavior_rules(
        txs=txs,
        address="0xwallet",
        since_ts=1735689600,
        inbound_ratio_threshold=0.7,
        min_unique_senders=3,
    )
    assert ok is True
    assert tx_count == 4
    assert round(inbound_ratio, 2) == 0.75
    assert unique_senders == 3
