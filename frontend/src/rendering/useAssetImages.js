import { useEffect, useState } from 'react';

import sewerTiles from '../assets/pixel-dungeon/environment/tiles_sewers.png';
import prisonTiles from '../assets/pixel-dungeon/environment/tiles_prison.png';
import terrainFeatures from '../assets/pixel-dungeon/environment/terrain_features.png';
import cavesTiles from '../assets/pixel-dungeon/environment/tiles_caves.png';
import cityTiles from '../assets/pixel-dungeon/environment/tiles_city.png';
import hallsTiles from '../assets/pixel-dungeon/environment/tiles_halls.png';
import water0 from '../assets/pixel-dungeon/environment/water0.png';
import water1 from '../assets/pixel-dungeon/environment/water1.png';
import water2 from '../assets/pixel-dungeon/environment/water2.png';
import water3 from '../assets/pixel-dungeon/environment/water3.png';
import water4 from '../assets/pixel-dungeon/environment/water4.png';
import warriorSprite from '../assets/pixel-dungeon/sprites/warrior.png';
import mageSprite from '../assets/pixel-dungeon/sprites/mage.png';
import rogueSprite from '../assets/pixel-dungeon/sprites/rogue.png';
import huntressSprite from '../assets/pixel-dungeon/sprites/huntress.png';
import itemsSprite from '../assets/pixel-dungeon/sprites/items.png';
import ratSprite from '../assets/pixel-dungeon/sprites/rat.png';
import crabSprite from '../assets/pixel-dungeon/sprites/crab.png';
import slimeSprite from '../assets/pixel-dungeon/sprites/slime.png';
import snakeSprite from '../assets/pixel-dungeon/sprites/snake.png';
import batSprite from '../assets/pixel-dungeon/sprites/bat.png';
import gnollSprite from '../assets/pixel-dungeon/sprites/gnoll.png';
import gooSprite from '../assets/pixel-dungeon/sprites/goo.png';
import scorpioSprite from '../assets/pixel-dungeon/sprites/scorpio.png';
import skeletonSprite from '../assets/pixel-dungeon/sprites/skeleton.png';
import thiefSprite from '../assets/pixel-dungeon/sprites/thief.png';
import dm100Sprite from '../assets/pixel-dungeon/sprites/dm100.png';
import guardSprite from '../assets/pixel-dungeon/sprites/guard.png';
import necromancerSprite from '../assets/pixel-dungeon/sprites/necromancer.png';

export default function useAssetImages() {
  const [assetImages, setAssetImages] = useState({
    tiles: null,           // sewers (default + back-compat)
    tilesByRegion: {       // SPD-style atlas per biome
      sewers: null,
      prison: null,
      caves: null,
      city: null,
      halls: null,
    },
    terrainFeatures: null,
    waterFrames: [null, null, null, null, null],
    warrior: null,
    mage: null,
    rogue: null,
    huntress: null,
    items: null,
    rat: null,
    crab: null,
    slime: null,
    snake: null,
    bat: null,
    gnoll: null,
    goo: null,
    scorpio: null,
    skeleton: null,
    thief: null,
    dm100: null,
    guard: null,
    necromancer: null,
  });

  useEffect(() => {
    const loadImage = (src, key, onLoad) => {
      const img = new Image();
      img.src = src;
      img.onload = () => {
        if (onLoad) {
          onLoad(img);
        } else {
          setAssetImages(prev => ({ ...prev, [key]: img }));
        }
      };
    };

    const loadWaterFrame = (src, frameIndex) => {
      loadImage(src, null, (img) => {
        setAssetImages(prev => {
          const nextFrames = prev.waterFrames.slice();
          nextFrames[frameIndex] = img;
          return { ...prev, waterFrames: nextFrames };
        });
      });
    };

    const loadRegionTiles = (src, regionKey) => {
      loadImage(src, null, (img) => {
        setAssetImages(prev => ({
          ...prev,
          tilesByRegion: { ...prev.tilesByRegion, [regionKey]: img },
          // Keep legacy `tiles` pointing at sewers so existing callers
          // that haven't migrated yet still work.
          ...(regionKey === 'sewers' ? { tiles: img } : {}),
        }));
      });
    };

    loadRegionTiles(sewerTiles, 'sewers');
    loadRegionTiles(prisonTiles, 'prison');
    loadRegionTiles(cavesTiles, 'caves');
    loadRegionTiles(cityTiles, 'city');
    loadRegionTiles(hallsTiles, 'halls');
    loadImage(terrainFeatures, 'terrainFeatures');
    loadWaterFrame(water0, 0);
    loadWaterFrame(water1, 1);
    loadWaterFrame(water2, 2);
    loadWaterFrame(water3, 3);
    loadWaterFrame(water4, 4);
    loadImage(warriorSprite, 'warrior');
    loadImage(mageSprite, 'mage');
    loadImage(rogueSprite, 'rogue');
    loadImage(huntressSprite, 'huntress');
    loadImage(itemsSprite, 'items');
    loadImage(ratSprite, 'rat');
    loadImage(crabSprite, 'crab');
    loadImage(slimeSprite, 'slime');
    loadImage(snakeSprite, 'snake');
    loadImage(batSprite, 'bat');
    loadImage(gnollSprite, 'gnoll');
    loadImage(gooSprite, 'goo');
    loadImage(scorpioSprite, 'scorpio');
    loadImage(skeletonSprite, 'skeleton');
    loadImage(thiefSprite, 'thief');
    loadImage(dm100Sprite, 'dm100');
    loadImage(guardSprite, 'guard');
    loadImage(necromancerSprite, 'necromancer');
  }, []);

  return assetImages;
}
