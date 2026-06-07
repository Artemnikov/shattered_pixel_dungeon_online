import atkBowSound from '../assets/pixel-dungeon/audio/atk_bow.mp3';
import zapSound from '../assets/pixel-dungeon/audio/zap.mp3';
import hitMagicSound from '../assets/pixel-dungeon/audio/hit_magic.mp3';
import stepSound from '../assets/pixel-dungeon/audio/step.mp3';
import hitArrowSound from '../assets/pixel-dungeon/audio/hit_arrow.mp3';
import hitSlashSound from '../assets/pixel-dungeon/audio/hit_slash.mp3';
import hitBodySound from '../assets/pixel-dungeon/audio/hit.mp3';
import hitStrongSound from '../assets/sounds/hit_strong.mp3';
import healthWarnSound from '../assets/pixel-dungeon/audio/health_warn.mp3';
import clickSound from '../assets/pixel-dungeon/audio/click.mp3';
import itemSound from '../assets/sounds/item.mp3';
import deathSound from '../assets/sounds/death.mp3';
import secretSound from '../assets/sounds/secret.mp3';
import waterStepSound from '../assets/sounds/water.mp3';
import grassStepSound from '../assets/sounds/grass.mp3';
import descendSound from '../assets/pixel-dungeon/audio/descend.mp3';
import drinkSound from '../assets/sounds/drink.mp3';
import throwSound from '../assets/sounds/miss.mp3';
import levelUpSound from '../assets/sounds/levelup.mp3';
import trapSound from '../assets/sounds/trap.mp3';
import chargeupSound from '../assets/pixel-dungeon/audio/chargeup.mp3';
import burningSound from '../assets/pixel-dungeon/audio/burning.mp3';
import bossSound from '../assets/pixel-dungeon/audio/boss.mp3';
import alertSound from '../assets/pixel-dungeon/audio/alert.mp3';
import { effectiveSfxVolume } from '../menu/menuSettings';

class AudioManager {
    constructor() {
        this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        this.sounds = {};
        this.enabled = true;
        this.loadedSounds = {};

        // master gain for all SFX, driven by user settings (volume + mute)
        this.masterGain = this.audioCtx.createGain();
        this.masterGain.gain.value = effectiveSfxVolume();
        this.masterGain.connect(this.audioCtx.destination);

        this.loadSound('ATTACK_BOW', atkBowSound);
        this.loadSound('THROW', throwSound);
        this.loadSound('MISS', throwSound);
        this.loadSound('ATTACK_MAGIC', zapSound);
        this.loadSound('HIT_MAGIC', hitMagicSound);
        this.loadSound('STEP', stepSound);
        this.loadSound('STEP_WATER', waterStepSound);
        this.loadSound('STEP_GRASS', grassStepSound);
        this.loadSound('HIT_ARROW', hitArrowSound);
        this.loadSound('HIT_SLASH', hitSlashSound);
        this.loadSound('HIT_STRONG', hitStrongSound);
        this.loadSound('HIT_BODY', hitBodySound);
        this.loadSound('HEALTH_WARN', healthWarnSound);
        this.loadSound('CLICK', clickSound);
        this.loadSound('PICKUP', itemSound);
        this.loadSound('DEATH', deathSound);
        this.loadSound('SECRET', secretSound);
        this.loadSound('STAIRS_DOWN', descendSound);
        this.loadSound('DRINK', drinkSound);
        this.loadSound('LEVELUP', levelUpSound);
        this.loadSound('TRAP', trapSound);
        this.loadSound('CHARGEUP', chargeupSound);
        this.loadSound('BURNING', burningSound);
        this.loadSound('BOSS', bossSound);
        this.loadSound('ALERT', alertSound);

        const doorSounds = import.meta.glob('../assets/sounds/door_open.mp3', { eager: true, query: '?url' });
        const doorUrl = doorSounds['../assets/sounds/door_open.mp3']?.default;
        if (doorUrl) this.loadSound('DOOR_OPEN', doorUrl);
    }

    async loadSound(name, src) {
        try {
            console.log(`[Audio] Attempting to load sound: ${name} from ${src}`);
            const response = await fetch(src);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const arrayBuffer = await response.arrayBuffer();
            const audioBuffer = await this.audioCtx.decodeAudioData(arrayBuffer);
            this.loadedSounds[name] = audioBuffer;
            console.log(`[Audio] Successfully loaded sound: ${name}`);
        } catch (e) {
            console.error(`[Audio] Failed to load sound ${name}:`, e);
        }
    }

    play(soundName, rate = 1.0) {
        if (!this.enabled) return;
        this.masterGain.gain.value = effectiveSfxVolume();
        if (this.audioCtx.state === 'suspended') {
            this.audioCtx.resume();
        }

        if (this.loadedSounds[soundName]) {
            this.playSoundBuffer(this.loadedSounds[soundName], rate);
            return;
        }

        // Fallback to synthesized sounds for unmatched names
        switch (soundName) {
            case 'MOVE':
                this.playTone(200, 'sine', 0.05, 0.1);
                break;
            case 'ATTACK':
                this.playTone(100, 'sawtooth', 0.1, 0.3); // aggressive sound
                this.playTone(150, 'sawtooth', 0.1, 0.3, 0.05);
                break;
            case 'DAMAGE':
                this.playTone(100, 'square', 0.2, 0.3);
                this.playTone(80, 'square', 0.2, 0.3, 0.1);
                break;
            case 'DEATH':
                this.playTone(150, 'sawtooth', 0.5, 0.5);
                this.playTone(100, 'sawtooth', 0.5, 0.5, 0.2);
                this.playTone(50, 'sawtooth', 0.8, 0.8, 0.4);
                break;
            case 'PICKUP':
                this.playTone(400, 'sine', 0.1, 0.1);
                this.playTone(600, 'sine', 0.1, 0.1, 0.05);
                break;
            case 'DRINK':
                this.playTone(300, 'triangle', 0.1, 0.1);
                this.playTone(350, 'triangle', 0.1, 0.1, 0.1);
                this.playTone(400, 'triangle', 0.2, 0.2, 0.2);
                break;
            case 'STAIRS_DOWN':
                this.playTone(200, 'sine', 0.5, 0.5);
                this.playTone(150, 'sine', 0.5, 0.5, 0.2);
                this.playTone(100, 'sine', 0.5, 0.5, 0.4);
                break;
            case 'REVIVE':
                this.playTone(300, 'sine', 0.5, 0.5);
                this.playTone(400, 'sine', 0.5, 0.5, 0.2);
                this.playTone(500, 'sine', 0.5, 0.5, 0.4);
                break;
            case 'DOOR_OPEN':
                this.playTone(300, 'triangle', 0.15, 0.2);
                this.playTone(200, 'triangle', 0.25, 0.15, 0.1);
                break;
            default:
                // console.log(`Sound not found: ${soundName}`);
                break;
        }
    }

    playStep(tileType) {
        if (!this.enabled) return;
        this.masterGain.gain.value = effectiveSfxVolume();
        const rate = 0.9 + Math.random() * 0.2;
        let key = 'STEP';
        if (tileType === 7) key = 'STEP_WATER';
        else if (tileType === 9) key = 'STEP_GRASS';
        if (this.loadedSounds[key]) {
            this.playSoundBuffer(this.loadedSounds[key], rate);
        } else {
            this.playTone(200, 'sine', 0.05, 0.1);
        }
    }

    playNoise(duration, vol, filterType, filterFreq) {
        const bufferSize = this.audioCtx.sampleRate * duration;
        const buffer = this.audioCtx.createBuffer(1, bufferSize, this.audioCtx.sampleRate);
        const data = buffer.getChannelData(0);

        for (let i = 0; i < bufferSize; i++) {
            data[i] = Math.random() * 2 - 1;
        }

        const noise = this.audioCtx.createBufferSource();
        noise.buffer = buffer;

        const gain = this.audioCtx.createGain();
        gain.gain.setValueAtTime(vol, this.audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, this.audioCtx.currentTime + duration);

        if (filterType) {
            const filter = this.audioCtx.createBiquadFilter();
            filter.type = filterType;
            filter.frequency.value = filterFreq;
            noise.connect(filter);
            filter.connect(gain);
        } else {
            noise.connect(gain);
        }

        gain.connect(this.masterGain);
        noise.start();
    }

    playSoundBuffer(buffer, rate = 1.0) {
        const source = this.audioCtx.createBufferSource();
        source.buffer = buffer;
        source.playbackRate.value = rate;
        source.connect(this.masterGain);
        source.start(0);
    }

    playTone(freq, type, duration, vol, delay = 0) {
        const osc = this.audioCtx.createOscillator();
        const gain = this.audioCtx.createGain();

        osc.type = type;
        osc.frequency.setValueAtTime(freq, this.audioCtx.currentTime + delay);

        gain.gain.setValueAtTime(vol, this.audioCtx.currentTime + delay);
        gain.gain.exponentialRampToValueAtTime(0.01, this.audioCtx.currentTime + delay + duration);

        osc.connect(gain);
        gain.connect(this.masterGain);

        osc.start(this.audioCtx.currentTime + delay);
        osc.stop(this.audioCtx.currentTime + delay + duration);
    }
}

export default new AudioManager();
