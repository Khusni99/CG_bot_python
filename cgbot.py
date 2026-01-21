#!/usr/bin/env python3
"""
Crypto.Games Dice Bot - Terminal Version
Preset Strategi Lengkap dengan 10 Strategi Terbaik
"""

import sys
import time
import requests
import random
import string
import json
import math
import re
import threading
import signal
import os
import shutil
from datetime import datetime
from typing import Dict, Optional, Any, List, Tuple
from dataclasses import dataclass, field
from collections import deque

# ============== KONFIGURASI ==============
VERSION = "5.0.0"
API_BASE_URL = "https://api.crypto.games/v1"
REQUEST_TIMEOUT = (2, 3)
MIN_BET = 0.00000001
FAUCET_BALANCE = 0.00000050
MIN_DELAY = 50
MAX_RETRIES = 3
SAVE_FILE = "bot_config.json"

# ============== DATA CLASSES ==============

@dataclass
class BetResult:
    """Hasil dari setiap taruhan"""
    bet_id: int
    roll: float
    profit: float
    balance: float
    success: bool
    timestamp: float

@dataclass
class Strategy:
    """Setting strategi"""
    name: str = "Faucet Farming"
    bet_amount: float = MIN_BET
    chance: float = 49.5
    payout: float = 2.0
    under_over: bool = True
    auto_stop_profit: float = 0.00000100
    auto_stop_loss: float = 0.00000025
    max_consecutive_losses: int = 5
    increase_on_loss: bool = True
    loss_increase_multiplier: float = 2.0
    decrease_on_win: bool = False
    win_decrease_multiplier: float = 0.5
    max_bet_percentage: float = 30.0
    min_bet_percentage: float = 1.0
    reset_after_target: bool = True
    take_profit_percentage: float = 50.0
    stop_loss_percentage: float = 50.0
    strategy_type: str = "preset"  # mining, daily_target, aggressive, etc.

@dataclass
class BotConfig:
    """Konfigurasi bot"""
    api_key: str = ""
    coin: str = "BTC"
    delay_ms: int = 300
    strategy: Strategy = field(default_factory=Strategy)
    running: bool = False
    initial_balance: float = FAUCET_BALANCE
    session_start: float = 0.0
    daily_profit_target: float = 0.0  # Target profit harian

# ============== TERMINAL MANAGER ==============

class TerminalManager:
    """Mengelola tampilan terminal dengan responsif"""
    
    # Color codes untuk Windows dan Unix
    if os.name == 'nt':  # Windows
        RESET = ""
        BOLD = ""
        GREEN = ""
        RED = ""
        YELLOW = ""
        BLUE = ""
        MAGENTA = ""
        CYAN = ""
        WHITE = ""
        GRAY = ""
    else:  # Unix/Linux/Mac
        RESET = "\033[0m"
        BOLD = "\033[1m"
        GREEN = "\033[92m"
        RED = "\033[91m"
        YELLOW = "\033[93m"
        BLUE = "\033[94m"
        MAGENTA = "\033[95m"
        CYAN = "\033[96m"
        WHITE = "\033[97m"
        GRAY = "\033[90m"
    
    def __init__(self):
        self.terminal_width = self.get_terminal_width()
        self.last_width_check = time.time()
        self.width_check_interval = 1.0
        
        # Enable ANSI colors di Windows 10+
        if os.name == 'nt':
            self._enable_windows_colors()
    
    def _enable_windows_colors(self):
        """Enable ANSI color support di Windows"""
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            
            # Set color codes untuk Windows dengan ANSI support
            self.RESET = "\033[0m"
            self.BOLD = "\033[1m"
            self.GREEN = "\033[92m"
            self.RED = "\033[91m"
            self.YELLOW = "\033[93m"
            self.BLUE = "\033[94m"
            self.MAGENTA = "\033[95m"
            self.CYAN = "\033[96m"
            self.WHITE = "\033[97m"
            self.GRAY = "\033[90m"
        except:
            pass
    
    def get_terminal_width(self) -> int:
        """Mendapatkan lebar terminal saat ini"""
        try:
            return shutil.get_terminal_size().columns
        except:
            return 80
    
    def check_and_update_width(self):
        """Cek dan update lebar terminal jika berubah"""
        current_time = time.time()
        if current_time - self.last_width_check >= self.width_check_interval:
            self.terminal_width = self.get_terminal_width()
            self.last_width_check = current_time
    
    def center_text(self, text: str, width: int = None) -> str:
        """Center text dengan lebar tertentu"""
        if width is None:
            width = self.terminal_width
        return text.center(width)
    
    def create_box(self, title: str, content: str = "", padding: int = 1) -> str:
        """Membuat box dengan border"""
        self.check_and_update_width()
        width = self.terminal_width - 4
        
        width = max(60, min(width, 120))
        
        lines = []
        
        top_border = "╔" + "═" * (width - 2) + "╗"
        lines.append(self.CYAN + top_border + self.RESET)
        
        title_line = f"║ {self.BOLD}{self.WHITE}{title}{self.RESET}"
        title_line = title_line.ljust(width - 1) + "║"
        lines.append(self.CYAN + title_line + self.RESET)
        
        separator = "╠" + "═" * (width - 2) + "╣"
        lines.append(self.CYAN + separator + self.RESET)
        
        if content:
            content_lines = content.split('\n')
            for line in content_lines:
                while len(line) > width - 4:
                    wrap_point = line[:width-4].rfind(' ')
                    if wrap_point == -1:
                        wrap_point = width - 4
                    wrapped_line = line[:wrap_point]
                    lines.append(self.CYAN + "║ " + self.RESET + wrapped_line.ljust(width - 3) + self.CYAN + "║" + self.RESET)
                    line = line[wrap_point:].strip()
                lines.append(self.CYAN + "║ " + self.RESET + line.ljust(width - 3) + self.CYAN + "║" + self.RESET)
        
        bottom_border = "╚" + "═" * (width - 2) + "╝"
        lines.append(self.CYAN + bottom_border + self.RESET)
        
        return "\n".join(lines)
    
    def create_horizontal_line(self, char: str = "─") -> str:
        """Membuat garis horizontal"""
        self.check_and_update_width()
        return self.GRAY + char * self.terminal_width + self.RESET
    
    def clear_screen(self):
        """Membersihkan layar terminal"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_header(self):
        """Menampilkan header aplikasi"""
        self.clear_screen()
        title = f"CRYPTO.GAMES DICE BOT v{VERSION}"
        subtitle = "10 PRESET STRATEGI TERBAIK"
        
        print(self.create_horizontal_line("═"))
        print(self.center_text(f"{self.BOLD}{self.CYAN}{title}{self.RESET}"))
        print(self.center_text(f"{self.YELLOW}{subtitle}{self.RESET}"))
        print(self.create_horizontal_line("═"))
        print()
    
    def print_menu(self, current_balance: float = 0.0, running: bool = False):
        """Menampilkan menu utama"""
        status_color = self.GREEN if running else self.RED
        status_icon = "▶️ " if running else "⏸️ "
        status_text = f"{status_icon} Bot is {status_color}{'RUNNING' if running else 'STOPPED'}{self.RESET}"
        
        if current_balance > 0:
            balance_text = f"│ Balance: {self.GREEN}{current_balance:.8f} BTC{self.RESET}"
        else:
            balance_text = ""
        
        menu_items = [
            f"{self.YELLOW}[1]{self.RESET} Setup API Configuration",
            f"{self.YELLOW}[2]{self.RESET} Select Preset Strategy",
            f"{self.YELLOW}[3]{self.RESET} Start Bot",
            f"{self.YELLOW}[4]{self.RESET} Stop Bot",
            f"{self.YELLOW}[5]{self.RESET} Check Balance",
            f"{self.YELLOW}[6]{self.RESET} View Statistics",
            f"{self.YELLOW}[7]{self.RESET} View Current Settings",
            f"{self.YELLOW}[8]{self.RESET} Clear Screen",
            f"{self.YELLOW}[9]{self.RESET} Exit"
        ]
        
        print(self.create_box("MAIN MENU", "\n".join(menu_items)))
        
        if balance_text:
            print(balance_text)
        
        print(f"\n{self.CYAN}Select option (1-9): {self.RESET}", end="")
    
    def print_log(self, message: str, icon: str = "📝", color: str = "white"):
        """Menampilkan log message dengan timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        color_map = {
            "green": self.GREEN,
            "red": self.RED,
            "yellow": self.YELLOW,
            "blue": self.BLUE,
            "cyan": self.CYAN,
            "white": self.WHITE,
            "gray": self.GRAY
        }
        
        color_code = color_map.get(color, self.WHITE)
        
        max_message_len = self.terminal_width - 20
        
        if len(message) > max_message_len:
            message = message[:max_message_len-3] + "..."
        
        print(f"{self.GRAY}[{timestamp}]{self.RESET} {icon} {color_code}{message}{self.RESET}")
    
    def print_bet_result(self, result: BetResult, total_profit: float, 
                        consecutive_wins: int, consecutive_losses: int):
        """Menampilkan hasil bet dengan format yang rapi"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        icon = "✅" if result.profit > 0 else "❌"
        profit_color = self.GREEN if result.profit > 0 else self.RED
        profit_sign = "+" if result.profit > 0 else ""
        
        if consecutive_wins > 0:
            streak_text = f"{self.GREEN}↑{consecutive_wins}{self.RESET}"
        elif consecutive_losses > 0:
            streak_text = f"{self.RED}↓{consecutive_losses}{self.RESET}"
        else:
            streak_text = "➖"
        
        if self.terminal_width >= 100:
            print(f"{self.GRAY}[{timestamp}]{self.RESET} {icon} "
                  f"Roll: {result.roll:6.3f} │ "
                  f"Profit: {profit_color}{profit_sign}{result.profit:12.8f}{self.RESET} │ "
                  f"Balance: {result.balance:12.8f} │ "
                  f"Total: {self.CYAN}{total_profit:12.8f}{self.RESET} │ "
                  f"Streak: {streak_text}")
        
        elif self.terminal_width >= 80:
            print(f"{self.GRAY}[{timestamp}]{self.RESET} {icon} "
                  f"Roll: {result.roll:6.3f} │ "
                  f"Profit: {profit_color}{profit_sign}{result.profit:10.8f}{self.RESET} │ "
                  f"Balance: {result.balance:10.8f} │ "
                  f"Total: {self.CYAN}{total_profit:10.8f}{self.RESET}")
        
        else:
            print(f"{self.GRAY}[{timestamp}]{self.RESET} {icon} "
                  f"R:{result.roll:5.1f} "
                  f"P:{profit_color}{profit_sign}{result.profit:.8f}{self.RESET} "
                  f"B:{result.balance:.8f}")
    
    def print_stats(self, stats: Dict):
        """Menampilkan statistics dalam box"""
        if not stats:
            return
        
        total_bets = stats.get('total_bets', 0)
        total_wins = stats.get('total_wins', 0)
        total_losses = stats.get('total_losses', 0)
        total_profit = stats.get('total_profit', 0.0)
        current_balance = stats.get('current_balance', 0.0)
        win_streak = stats.get('consecutive_wins', 0)
        loss_streak = stats.get('consecutive_losses', 0)
        bps = stats.get('bets_per_second', 0.0)
        session_time = stats.get('session_time', 0.0)
        daily_target = stats.get('daily_progress', 0.0)
        
        win_rate = (total_wins / total_bets * 100) if total_bets > 0 else 0
        profit_color = self.GREEN if total_profit >= 0 else self.RED
        
        lines = []
        lines.append(f"Total Bets: {self.YELLOW}{total_bets}{self.RESET}")
        lines.append(f"Wins: {self.GREEN}{total_wins}{self.RESET} │ Losses: {self.RED}{total_losses}{self.RESET}")
        lines.append(f"Win Rate: {self.CYAN}{win_rate:.2f}%{self.RESET}")
        lines.append(f"Total Profit: {profit_color}{total_profit:.8f} BTC{self.RESET}")
        lines.append(f"Current Balance: {self.GREEN}{current_balance:.8f} BTC{self.RESET}")
        lines.append(f"Win Streak: {self.GREEN}{win_streak}{self.RESET} │ Loss Streak: {self.RED}{loss_streak}{self.RESET}")
        
        if daily_target > 0:
            lines.append(f"Daily Target Progress: {self.MAGENTA}{daily_target:.1f}%{self.RESET}")
        
        lines.append(f"Bets/Second: {self.BLUE}{bps:.2f}{self.RESET}")
        lines.append(f"Session Time: {self.YELLOW}{session_time:.0f}s{self.RESET}")
        
        content = "\n".join(lines)
        print(self.create_box("📊 LIVE STATISTICS", content))
    
    def print_settings(self, config: BotConfig):
        """Menampilkan settings saat ini"""
        if not config or not config.strategy:
            return
        
        strat = config.strategy
        
        lines = []
        lines.append(f"API Key: {'***' + config.api_key[-4:] if config.api_key else 'Not Set'}")
        lines.append(f"Coin: {self.YELLOW}{config.coin}{self.RESET}")
        lines.append(f"Delay: {config.delay_ms}ms")
        lines.append("")
        lines.append(f"{self.BOLD}Strategy: {strat.name}{self.RESET}")
        lines.append(f"Type: {strat.strategy_type}")
        lines.append(f"Bet Amount: {strat.bet_amount:.8f} BTC")
        lines.append(f"Chance: {strat.chance}%")
        lines.append(f"Payout: {strat.payout}x")
        lines.append(f"Direction: {'Under' if strat.under_over else 'Over'}")
        lines.append(f"Stop Profit: {strat.auto_stop_profit:.8f} BTC")
        lines.append(f"Stop Loss: {strat.auto_stop_loss:.8f} BTC")
        lines.append(f"Max Consecutive Losses: {strat.max_consecutive_losses}")
        
        content = "\n".join(lines)
        print(self.create_box("⚙️ CURRENT SETTINGS", content))
    
    def get_input(self, prompt: str, default: str = "") -> str:
        """Mendapatkan input dari user"""
        self.check_and_update_width()
        
        if default:
            full_prompt = f"{self.CYAN}{prompt} [{default}]: {self.RESET}"
        else:
            full_prompt = f"{self.CYAN}{prompt}: {self.RESET}"
        
        if len(full_prompt) > self.terminal_width - 10:
            print(f"{self.CYAN}{prompt}{self.RESET}")
            if default:
                print(f"{self.GRAY}Default: {default}{self.RESET}")
            full_prompt = f"{self.CYAN}> {self.RESET}"
        
        try:
            user_input = input(full_prompt).strip()
            if not user_input and default:
                return default
            return user_input
        except (KeyboardInterrupt, EOFError):
            return ""
    
    def get_float_input(self, prompt: str, default: float = 0.0, 
                       min_val: float = None, max_val: float = None) -> float:
        """Mendapatkan input float dengan validasi"""
        while True:
            try:
                value_str = self.get_input(prompt, str(default))
                if not value_str and default is not None:
                    value = default
                else:
                    value = float(value_str)
                
                if min_val is not None and value < min_val:
                    self.print_log(f"Minimum value is {min_val}", "⚠️", "yellow")
                    continue
                
                if max_val is not None and value > max_val:
                    self.print_log(f"Maximum value is {max_val}", "⚠️", "yellow")
                    continue
                
                return value
            except ValueError:
                self.print_log("Invalid number. Please try again.", "❌", "red")

# ============== BOT ENGINE ==============

class CryptoGamesAPI:
    """Client untuk API Crypto.Games"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        })
    
    def get_balance(self, coin: str, api_key: str) -> Optional[float]:
        """Mendapatkan balance dari API"""
        try:
            url = f"{API_BASE_URL}/balance/{coin}/{api_key}"
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            
            if response.status_code == 200:
                data = response.json()
                return float(data['Balance'])
        except Exception as e:
            print(f"Error getting balance: {e}")
        return None
    
    def place_bet(self, coin: str, api_key: str, bet_data: Dict) -> Optional[BetResult]:
        """Menempatkan taruhan"""
        try:
            url = f"{API_BASE_URL}/placebet/{coin}/{api_key}"
            response = self.session.post(url, json=bet_data, timeout=REQUEST_TIMEOUT)
            
            if response.status_code == 200:
                data = response.json()
                return BetResult(
                    bet_id=data.get('BetId', 0),
                    roll=data.get('Roll', 0),
                    profit=float(data.get('Profit', 0)),
                    balance=float(data.get('Balance', 0)),
                    success=True,
                    timestamp=time.time()
                )
        except Exception as e:
            print(f"Error placing bet: {e}")
        return None

class DiceBot:
    """Mesin utama bot dice dengan 10 preset strategi"""
    
    # ============== PRESET STRATEGIES ==============
    PRESET_STRATEGIES = {
        1: Strategy(
            name="💰 FAUCET FARMING",
            bet_amount=MIN_BET,
            chance=49.5,
            payout=2.0,
            under_over=True,
            auto_stop_profit=0.00000100,
            auto_stop_loss=0.00000025,
            max_consecutive_losses=5,
            increase_on_loss=True,
            loss_increase_multiplier=2.0,
            decrease_on_win=False,
            max_bet_percentage=30.0,
            min_bet_percentage=1.0,
            strategy_type="faucet"
        ),
        2: Strategy(
            name="⛏️ BITCOIN MINING",
            bet_amount=MIN_BET,
            chance=49.5,
            payout=2.0,
            under_over=True,
            auto_stop_profit=0.00000500,
            auto_stop_loss=0.00000010,
            max_consecutive_losses=10,
            increase_on_loss=True,
            loss_increase_multiplier=1.5,
            decrease_on_win=True,
            win_decrease_multiplier=0.8,
            max_bet_percentage=20.0,
            min_bet_percentage=0.5,
            strategy_type="mining"
        ),
        3: Strategy(
            name="🎯 DAILY 10% PROFIT",
            bet_amount=MIN_BET * 2,
            chance=49.5,
            payout=2.0,
            under_over=True,
            auto_stop_profit=0.00000055,  # 10% dari 0.00000050
            auto_stop_loss=0.00000010,
            max_consecutive_losses=3,
            increase_on_loss=False,
            decrease_on_win=True,
            win_decrease_multiplier=0.7,
            max_bet_percentage=15.0,
            min_bet_percentage=1.0,
            strategy_type="daily_target"
        ),
        4: Strategy(
            name="🚀 AGGRESSIVE GROWTH",
            bet_amount=MIN_BET * 3,
            chance=40.0,
            payout=2.5,
            under_over=True,
            auto_stop_profit=0.00000200,
            auto_stop_loss=0.00000015,
            max_consecutive_losses=3,
            increase_on_loss=True,
            loss_increase_multiplier=2.5,
            decrease_on_win=False,
            max_bet_percentage=40.0,
            min_bet_percentage=2.0,
            strategy_type="aggressive"
        ),
        5: Strategy(
            name="🛡️ SAFE GRINDING",
            bet_amount=MIN_BET,
            chance=51.0,
            payout=1.96,
            under_over=True,
            auto_stop_profit=0.00000030,
            auto_stop_loss=0.00000005,
            max_consecutive_losses=8,
            increase_on_loss=False,
            decrease_on_win=False,
            max_bet_percentage=10.0,
            min_bet_percentage=0.5,
            strategy_type="safe"
        ),
        6: Strategy(
            name="⚡ HIGH SPEED",
            bet_amount=MIN_BET,
            chance=49.5,
            payout=2.0,
            under_over=True,
            auto_stop_profit=0.00000020,
            auto_stop_loss=0.00000005,
            max_consecutive_losses=15,
            increase_on_loss=False,
            decrease_on_win=False,
            max_bet_percentage=5.0,
            min_bet_percentage=0.3,
            strategy_type="speed"
        ),
        7: Strategy(
            name="📈 MARTINGALE PRO",
            bet_amount=MIN_BET,
            chance=49.5,
            payout=2.0,
            under_over=True,
            auto_stop_profit=0.00000150,
            auto_stop_loss=0.00000020,
            max_consecutive_losses=6,
            increase_on_loss=True,
            loss_increase_multiplier=3.0,
            decrease_on_win=True,
            win_decrease_multiplier=0.5,
            max_bet_percentage=50.0,
            min_bet_percentage=1.0,
            strategy_type="martingale"
        ),
        8: Strategy(
            name="🎲 HIGH RISK REWARD",
            bet_amount=MIN_BET * 5,
            chance=33.33,
            payout=3.0,
            under_over=True,
            auto_stop_profit=0.00000500,
            auto_stop_loss=0.00000020,
            max_consecutive_losses=2,
            increase_on_loss=True,
            loss_increase_multiplier=4.0,
            decrease_on_win=False,
            max_bet_percentage=60.0,
            min_bet_percentage=5.0,
            strategy_type="high_risk"
        ),
        9: Strategy(
            name="💎 CONSERVATIVE MINING",
            bet_amount=MIN_BET,
            chance=49.75,
            payout=2.0,
            under_over=True,
            auto_stop_profit=0.00000080,
            auto_stop_loss=0.00000010,
            max_consecutive_losses=12,
            increase_on_loss=False,
            decrease_on_win=True,
            win_decrease_multiplier=0.9,
            max_bet_percentage=8.0,
            min_bet_percentage=0.3,
            strategy_type="conservative"
        ),
        10: Strategy(
            name="🏆 PROFESSIONAL",
            bet_amount=MIN_BET * 2,
            chance=48.0,
            payout=2.08,
            under_over=True,
            auto_stop_profit=0.00000300,
            auto_stop_loss=0.00000015,
            max_consecutive_losses=4,
            increase_on_loss=True,
            loss_increase_multiplier=2.0,
            decrease_on_win=True,
            win_decrease_multiplier=0.6,
            max_bet_percentage=25.0,
            min_bet_percentage=1.5,
            strategy_type="professional"
        )
    }
    
    def __init__(self, ui: TerminalManager):
        self.ui = ui
        self.api = CryptoGamesAPI()
        self.running = False
        self.stop_event = threading.Event()
        self.thread = None
        
        # Configuration
        self.config = BotConfig()
        
        # Statistics
        self.stats = {
            'total_bets': 0,
            'total_wins': 0,
            'total_losses': 0,
            'total_profit': 0.0,
            'total_wagered': 0.0,
            'consecutive_wins': 0,
            'consecutive_losses': 0,
            'current_balance': 0.0,
            'bets_per_second': 0.0,
            'session_time': 0.0,
            'max_bet_used': 0.0,
            'min_bet_used': float('inf'),
            'start_time': 0.0,
            'daily_progress': 0.0
        }
        
        # State
        self.current_bet = MIN_BET
        self.last_stats_update = time.time()
        self.bet_times = deque(maxlen=100)
        self.initial_balance = 0.0
        self.daily_target = 0.0
        self.daily_start_balance = 0.0
        
        # Load config jika ada
        self.load_config()
    
    def load_config(self):
        """Load konfigurasi dari file"""
        try:
            if os.path.exists(SAVE_FILE):
                with open(SAVE_FILE, 'r') as f:
                    data = json.load(f)
                    self.config.api_key = data.get('api_key', '')
                    self.config.coin = data.get('coin', 'BTC')
                    self.config.delay_ms = data.get('delay_ms', 300)
                    
                    strat_data = data.get('strategy', {})
                    self.config.strategy = Strategy(**strat_data)
                    
                self.ui.print_log("Configuration loaded from file", "📂", "green")
        except Exception as e:
            self.ui.print_log(f"Error loading config: {e}", "❌", "red")
    
    def save_config(self):
        """Simpan konfigurasi ke file"""
        try:
            data = {
                'api_key': self.config.api_key,
                'coin': self.config.coin,
                'delay_ms': self.config.delay_ms,
                'strategy': self.config.strategy.__dict__
            }
            
            with open(SAVE_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            
            self.ui.print_log("Configuration saved to file", "💾", "green")
        except Exception as e:
            self.ui.print_log(f"Error saving config: {e}", "❌", "red")
    
    def setup_api_config(self):
        """Setup konfigurasi API"""
        self.ui.print_header()
        self.ui.print_log("Setting up API Configuration", "🔧", "blue")
        
        api_key = self.ui.get_input("Enter your API key", self.config.api_key)
        if not api_key:
            self.ui.print_log("Setup cancelled", "⚠️", "yellow")
            return
        
        coin = self.ui.get_input("Enter coin (BTC, LTC, DOGE, ETH)", self.config.coin)
        delay = self.ui.get_float_input("Delay between bets (ms)", self.config.delay_ms, 50, 5000)
        
        self.config.api_key = api_key
        self.config.coin = coin.upper()
        self.config.delay_ms = int(delay)
        
        self.save_config()
        self.ui.print_log(f"API configured: Coin={coin}, Delay={delay}ms", "✅", "green")
    
    def select_preset_strategy(self):
        """Pilih dari 10 preset strategi"""
        self.ui.print_header()
        self.ui.print_log("Select Preset Strategy", "🎯", "blue")
        
        print("\n" + self.ui.create_box("📊 10 PRESET STRATEGIES", self._get_strategies_list()))
        
        try:
            choice = int(self.ui.get_input("Select strategy (1-10)", "1"))
        except ValueError:
            self.ui.print_log("Invalid selection", "❌", "red")
            return
        
        if 1 <= choice <= 10:
            selected_strategy = self.PRESET_STRATEGIES[choice]
            self.config.strategy = selected_strategy
            
            # Tampilkan detail strategi
            self.ui.print_header()
            self.ui.print_log(f"Selected: {selected_strategy.name}", "✅", "green")
            
            details = [
                f"Type: {selected_strategy.strategy_type}",
                f"Bet Amount: {selected_strategy.bet_amount:.8f} BTC",
                f"Win Chance: {selected_strategy.chance}%",
                f"Payout: {selected_strategy.payout}x",
                f"Stop Profit: {selected_strategy.auto_stop_profit:.8f} BTC",
                f"Stop Loss: {selected_strategy.auto_stop_loss:.8f} BTC",
                f"Max Loss Streak: {selected_strategy.max_consecutive_losses}",
                f"Increase on Loss: {'Yes' if selected_strategy.increase_on_loss else 'No'}",
                f"Max Bet: {selected_strategy.max_bet_percentage}% of balance"
            ]
            
            print(self.ui.create_box("📋 STRATEGY DETAILS", "\n".join(details)))
            
            confirm = self.ui.get_input("Load this strategy? (yes/no)", "yes")
            if confirm.lower() == 'yes':
                self.save_config()
                self.ui.print_log(f"Strategy '{selected_strategy.name}' loaded!", "🚀", "green")
            else:
                self.ui.print_log("Strategy selection cancelled", "⚠️", "yellow")
        else:
            self.ui.print_log("Invalid strategy number", "❌", "red")
    
    def _get_strategies_list(self) -> str:
        """Membuat daftar strategi untuk ditampilkan"""
        lines = []
        for num, strategy in self.PRESET_STRATEGIES.items():
            lines.append(f"{self.ui.YELLOW}[{num}]{self.ui.RESET} {strategy.name}")
            lines.append(f"   Type: {strategy.strategy_type} | Chance: {strategy.chance}% | Payout: {strategy.payout}x")
            lines.append(f"   Target: {strategy.auto_stop_profit:.8f} BTC | Stop: {strategy.auto_stop_loss:.8f} BTC")
            lines.append("")
        
        return "\n".join(lines)
    
    def check_balance(self):
        """Cek balance dari API"""
        if not self.config.api_key:
            self.ui.print_log("Please setup API key first", "⚠️", "yellow")
            return
        
        self.ui.print_log("Checking balance...", "🔄", "blue")
        
        balance = self.api.get_balance(self.config.coin, self.config.api_key)
        if balance is not None:
            self.stats['current_balance'] = balance
            self.ui.print_log(f"Balance: {balance:.8f} {self.config.coin}", "💰", "green")
            
            if self.initial_balance == 0:
                self.initial_balance = balance
                self.config.initial_balance = balance
                self.daily_start_balance = balance
        else:
            self.ui.print_log("Failed to get balance", "❌", "red")
    
    def calculate_next_bet(self) -> float:
        """Hitung jumlah taruhan berikutnya berdasarkan strategi"""
        if not self.config.strategy:
            return MIN_BET
        
        strat = self.config.strategy
        current_balance = self.stats['current_balance']
        
        # Base bet amount
        base_bet = strat.bet_amount
        
        # Adjust based on streaks
        if self.stats['consecutive_losses'] > 0 and strat.increase_on_loss:
            base_bet *= (strat.loss_increase_multiplier ** min(
                self.stats['consecutive_losses'], 
                strat.max_consecutive_losses
            ))
        
        elif self.stats['consecutive_wins'] > 0 and strat.decrease_on_win:
            base_bet *= (strat.win_decrease_multiplier ** self.stats['consecutive_wins'])
        
        # Apply percentage limits
        max_bet = current_balance * (strat.max_bet_percentage / 100.0)
        min_bet = current_balance * (strat.min_bet_percentage / 100.0)
        
        base_bet = max(min_bet, min(base_bet, max_bet))
        
        # Ensure minimum bet
        base_bet = max(base_bet, MIN_BET)
        
        # Update stats
        self.stats['max_bet_used'] = max(self.stats['max_bet_used'], base_bet)
        self.stats['min_bet_used'] = min(self.stats['min_bet_used'], base_bet)
        
        return round(base_bet, 8)
    
    def check_stop_conditions(self) -> bool:
        """Cek kondisi untuk menghentikan bot"""
        if not self.config.strategy:
            return True
        
        strat = self.config.strategy
        current_balance = self.stats['current_balance']
        total_profit = self.stats['total_profit']
        
        # Check profit target
        if strat.auto_stop_profit > 0 and total_profit >= strat.auto_stop_profit:
            self.ui.print_log(f"🎯 Profit target reached! (+{total_profit:.8f} BTC)", "🎯", "green")
            return False
        
        # Check stop loss
        if strat.auto_stop_loss > 0 and self.initial_balance - current_balance >= strat.auto_stop_loss:
            self.ui.print_log(f"🛑 Stop loss triggered! (-{self.initial_balance - current_balance:.8f} BTC)", "🛑", "red")
            return False
        
        # Check max consecutive losses
        if strat.max_consecutive_losses > 0 and \
           self.stats['consecutive_losses'] >= strat.max_consecutive_losses:
            self.ui.print_log(f"⚠️ Max consecutive losses reached ({self.stats['consecutive_losses']})", "⚠️", "yellow")
            return False
        
        # Check daily target progress (untuk strategi daily target)
        if strat.strategy_type == "daily_target" and self.daily_start_balance > 0:
            daily_profit = current_balance - self.daily_start_balance
            daily_target = self.daily_start_balance * 0.10  # 10% target
            
            if daily_profit >= daily_target:
                self.ui.print_log(f"🎯 Daily 10% target achieved! (+{daily_profit:.8f} BTC)", "🎯", "green")
                return False
        
        return True
    
    def start(self):
        """Start bot"""
        if not self.config.api_key:
            self.ui.print_log("Please setup API key first", "⚠️", "yellow")
            return
        
        if self.running:
            self.ui.print_log("Bot is already running", "⚠️", "yellow")
            return
        
        # Cek balance awal
        self.check_balance()
        
        if self.stats['current_balance'] <= 0:
            self.ui.print_log("Insufficient balance to start", "❌", "red")
            return
        
        self.initial_balance = self.stats['current_balance']
        self.config.initial_balance = self.initial_balance
        self.config.session_start = time.time()
        self.daily_start_balance = self.initial_balance
        
        # Reset stats
        self.stats['start_time'] = time.time()
        self.stats['total_bets'] = 0
        self.stats['total_wins'] = 0
        self.stats['total_losses'] = 0
        self.stats['total_profit'] = 0.0
        self.stats['total_wagered'] = 0.0
        self.stats['consecutive_wins'] = 0
        self.stats['consecutive_losses'] = 0
        self.stats['max_bet_used'] = 0.0
        self.stats['min_bet_used'] = float('inf')
        self.stats['daily_progress'] = 0.0
        
        # Tampilkan strategi yang dipilih
        self.ui.print_log(f"Starting with strategy: {self.config.strategy.name}", "🚀", "green")
        self.ui.print_log(f"Target: {self.config.strategy.auto_stop_profit:.8f} BTC | Stop Loss: {self.config.strategy.auto_stop_loss:.8f} BTC", "🎯", "cyan")
        
        # Start bot thread
        self.running = True
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        
        self.config.running = True
        self.ui.print_log("Bot started successfully!", "✅", "green")
    
    def stop(self):
        """Stop bot"""
        if not self.running:
            self.ui.print_log("Bot is not running", "⚠️", "yellow")
            return
        
        self.running = False
        self.stop_event.set()
        
        if self.thread:
            self.thread.join(timeout=2.0)
        
        self.config.running = False
        self.ui.print_log("Bot stopped", "⏹️", "yellow")
        
        # Tampilkan final stats
        self.update_stats_display()
    
    def _run_loop(self):
        """Loop utama bot"""
        bet_counter = 0
        
        while self.running and not self.stop_event.is_set():
            try:
                # Update stats display setiap 5 detik
                current_time = time.time()
                if current_time - self.last_stats_update >= 5.0:
                    self.update_stats_display()
                    self.last_stats_update = current_time
                
                # Cek stop conditions
                if not self.check_stop_conditions():
                    self.stop()
                    break
                
                # Hitung bet amount
                bet_amount = self.calculate_next_bet()
                
                # Generate client seed
                client_seed = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
                
                # Siapkan data bet
                bet_data = {
                    "Bet": bet_amount,
                    "Payout": self.config.strategy.payout,
                    "UnderOver": self.config.strategy.under_over,
                    "ClientSeed": client_seed
                }
                
                # Place bet
                result = None
                for retry in range(MAX_RETRIES):
                    result = self.api.place_bet(
                        self.config.coin,
                        self.config.api_key,
                        bet_data
                    )
                    if result:
                        break
                    time.sleep(0.1)
                
                if result:
                    # Update stats
                    self.stats['total_bets'] += 1
                    self.stats['total_wagered'] += bet_amount
                    self.stats['total_profit'] += result.profit
                    self.stats['current_balance'] = result.balance
                    
                    # Update streaks
                    if result.profit > 0:
                        self.stats['total_wins'] += 1
                        self.stats['consecutive_wins'] += 1
                        self.stats['consecutive_losses'] = 0
                    else:
                        self.stats['total_losses'] += 1
                        self.stats['consecutive_losses'] += 1
                        self.stats['consecutive_wins'] = 0
                    
                    # Update daily progress untuk strategi daily target
                    if self.config.strategy.strategy_type == "daily_target" and self.daily_start_balance > 0:
                        daily_profit = result.balance - self.daily_start_balance
                        daily_target = self.daily_start_balance * 0.10
                        if daily_target > 0:
                            self.stats['daily_progress'] = (daily_profit / daily_target) * 100
                    
                    # Tampilkan hasil
                    self.ui.print_bet_result(
                        result,
                        self.stats['total_profit'],
                        self.stats['consecutive_wins'],
                        self.stats['consecutive_losses']
                    )
                    
                    bet_counter += 1
                    self.bet_times.append(time.time())
                
                # Delay antara bets
                time.sleep(self.config.delay_ms / 1000.0)
                
            except Exception as e:
                self.ui.print_log(f"Error in betting loop: {e}", "❌", "red")
                time.sleep(1.0)
    
    def update_stats_display(self):
        """Update dan tampilkan statistics"""
        if self.stats['total_bets'] > 0:
            current_time = time.time()
            session_time = current_time - self.stats['start_time']
            
            # Calculate BPS
            if len(self.bet_times) >= 2:
                time_diff = self.bet_times[-1] - self.bet_times[0]
                if time_diff > 0:
                    self.stats['bets_per_second'] = len(self.bet_times) / time_diff
            
            self.stats['session_time'] = session_time
            
            # Tampilkan stats setiap 30 detik atau saat stop
            if session_time % 30 < 1 or not self.running:
                self.ui.print_stats(self.stats)
    
    def view_statistics(self):
        """Tampilkan statistics saat ini"""
        self.ui.print_header()
        if self.stats['total_bets'] > 0:
            self.ui.print_stats(self.stats)
        else:
            self.ui.print_log("No statistics available yet", "📊", "yellow")
        
        input("\nPress Enter to continue...")
    
    def view_settings(self):
        """Tampilkan settings saat ini"""
        self.ui.print_header()
        self.ui.print_settings(self.config)
        
        input("\nPress Enter to continue...")

# ============== MAIN APPLICATION ==============

def main():
    """Fungsi utama"""
    def signal_handler(sig, frame):
        print("\n\nInterrupted by user. Exiting...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Initialize terminal manager
    ui = TerminalManager()
    bot = DiceBot(ui)
    
    # Main loop
    while True:
        try:
            ui.print_header()
            ui.print_menu(bot.stats['current_balance'], bot.running)
            
            choice = input().strip()
            
            if choice == '1':
                bot.setup_api_config()
                input("\nPress Enter to continue...")
            
            elif choice == '2':
                bot.select_preset_strategy()
                input("\nPress Enter to continue...")
            
            elif choice == '3':
                bot.start()
                input("\nPress Enter to continue...")
            
            elif choice == '4':
                bot.stop()
                input("\nPress Enter to continue...")
            
            elif choice == '5':
                bot.check_balance()
                input("\nPress Enter to continue...")
            
            elif choice == '6':
                bot.view_statistics()
            
            elif choice == '7':
                bot.view_settings()
            
            elif choice == '8':
                continue
            
            elif choice == '9':
                if bot.running:
                    bot.stop()
                print("\nGoodbye! 👋")
                break
            
            else:
                ui.print_log("Invalid option. Please try again.", "❌", "red")
                time.sleep(1)
        
        except KeyboardInterrupt:
            print("\n\nExiting...")
            if bot.running:
                bot.stop()
            break
        
        except Exception as e:
            ui.print_log(f"Unexpected error: {e}", "💥", "red")
            time.sleep(2)

if __name__ == "__main__":
    main()