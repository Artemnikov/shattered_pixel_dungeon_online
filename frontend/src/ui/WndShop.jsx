// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 ArtemNikov
//
// Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenham
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
// See the GNU General Public License for more details.
//
import { useEffect } from 'react';
import AudioManager from '../audio/AudioManager';
import ItemIcon from './ItemIcon';

// Shopkeeper trade window (WndTradeItem.java): two lists side by side — the
// shop's stock (buy, priced via Shopkeeper.sellPrice) and the hero's sellable
// backpack items (sell, priced via Item.value()).
export default function WndShop({ npcId, stock, gold, backpackItems, onBuy, onSell, onClose }) {
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const sellable = (backpackItems || []).filter(i => (i.value || 0) > 0 && i.kind !== 'gold');

  return (
    <div className="wnd-overlay wnd-shop-overlay" onClick={onClose}>
      <div className="wnd-shop" onClick={(e) => e.stopPropagation()}>
        <button
          className="wnd-bag-close"
          onClick={() => { AudioManager.play('CLICK'); onClose(); }}
          aria-label="Close shop"
        >
          ✕
        </button>
        <div className="wnd-shop-header">
          <span className="wnd-shop-title">Shop</span>
          <span className="inv-gold">{gold ?? 0}<i className="inv-gold-icon" /></span>
        </div>
        <div className="wnd-shop-columns">
          <div className="wnd-shop-col">
            <div className="wnd-shop-col-title">Buy</div>
            <div className="wnd-shop-list">
              {stock.length === 0 && <div className="wnd-shop-empty">Nothing for sale</div>}
              {stock.map(item => (
                <button
                  key={item.id}
                  className="wnd-shop-row"
                  disabled={(gold ?? 0) < (item.value || 0)}
                  onClick={() => { AudioManager.play('CLICK'); onBuy(npcId, item.id); }}
                >
                  <ItemIcon item={item} size={28} />
                  <span className="wnd-shop-name">{item.name}</span>
                  <span className="wnd-shop-price">{item.value}<i className="inv-gold-icon" /></span>
                </button>
              ))}
            </div>
          </div>
          <div className="wnd-shop-col">
            <div className="wnd-shop-col-title">Sell</div>
            <div className="wnd-shop-list">
              {sellable.length === 0 && <div className="wnd-shop-empty">Nothing to sell</div>}
              {sellable.map(item => (
                <button
                  key={item.id}
                  className="wnd-shop-row"
                  onClick={() => { AudioManager.play('CLICK'); onSell(item.id); }}
                >
                  <ItemIcon item={item} size={28} />
                  <span className="wnd-shop-name">{item.name}</span>
                  <span className="wnd-shop-price">{item.value}<i className="inv-gold-icon" /></span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
