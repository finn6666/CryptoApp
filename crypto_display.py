from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.layout import Layout
from rich.columns import Columns
from rich import box
from crypto_analyzer import CryptoAnalyzer, CoinStatus, Coin
from crypto_visualizer import CryptoVisualizer
from typing import List
import sys

class CryptoDisplay:
    """Beautiful CLI display for cryptocurrency data"""
    
    def __init__(self):
        self.console = Console()
        self.analyzer = CryptoAnalyzer()
        self.visualizer = CryptoVisualizer()
        
    def show_header(self):
        """Display app header"""
        title = Text("🚀 CRYPTO INVESTMENT ANALYZER 🚀", style="bold magenta")
        subtitle = Text("Find the most attractive cryptocurrency opportunities", style="cyan")
        
        header_panel = Panel(
            f"{title}\n{subtitle}",
            box=box.DOUBLE,
            style="blue"
        )
        self.console.print(header_panel)
        self.console.print()
    
    def create_coin_table(self, coins: List[Coin], title: str, show_rank: bool = True) -> Table:
        """Create a formatted table for coins"""
        table = Table(title=title, box=box.ROUNDED, title_style="bold green")
        
        table.add_column("Symbol", style="cyan", no_wrap=True)
        table.add_column("Name", style="white")
        table.add_column("Score", style="yellow", justify="center")
        table.add_column("Price", style="green", justify="right")
        table.add_column("24h Change", justify="center")
        if show_rank:
            table.add_column("Rank", style="blue", justify="center")
        
        for coin in coins:
            # Format price
            price_str = f"${coin.price:,.2f}" if coin.price else "TBA"
            
            # Format 24h change with color
            if coin.price_change_24h_usd is not None:
                change = coin.price_change_24h_usd
                if change > 0:
                    change_str = f"[green]+{change:.1f}%[/green]"
                elif change < 0:
                    change_str = f"[red]{change:.1f}%[/red]"
                else:
                    change_str = "0.0%"
            else:
                change_str = "[dim]N/A[/dim]"
            
            # Format rank
            rank_str = str(coin.market_cap_rank) if coin.market_cap_rank else "-"
            
            # Score color coding
            score = coin.attractiveness_score
            if score >= 9.0:
                score_str = f"[bright_green]{score:.1f}[/bright_green]"
            elif score >= 8.0:
                score_str = f"[green]{score:.1f}[/green]"
            elif score >= 7.0:
                score_str = f"[yellow]{score:.1f}[/yellow]"
            else:
                score_str = f"[red]{score:.1f}[/red]"
            
            row_data = [coin.symbol, coin.name, score_str, price_str, change_str]
            if show_rank:
                row_data.append(rank_str)
            
            table.add_row(*row_data)
        
        return table
    
    def show_top_opportunities(self):
        """Display top investment opportunities"""
        self.console.print("[bold blue]📈 TOP INVESTMENT OPPORTUNITIES[/bold blue]\n")
        
        # Get top coins overall
        top_coins = self.analyzer.get_top_coins(5)
        table = self.create_coin_table(top_coins, "🏆 Highest Rated Coins")
        self.console.print(table)
        self.console.print()
    
    def show_upcoming_presales(self):
        """Display upcoming presale opportunities"""
        upcoming = self.analyzer.get_upcoming_opportunities()
        if upcoming:
            self.console.print("[bold magenta]🔮 UPCOMING PRESALE OPPORTUNITIES[/bold magenta]\n")
            
            table = Table(title="💎 Early Investment Opportunities", box=box.ROUNDED)
            table.add_column("Symbol", style="cyan")
            table.add_column("Name", style="white")
            table.add_column("Score", style="yellow", justify="center")
            table.add_column("Launch Date", style="green")
            table.add_column("Presale Discount", style="bright_green", justify="center")
            table.add_column("Key Features", style="dim")
            
            for coin in upcoming:
                score_str = f"[bright_green]{coin.attractiveness_score:.1f}[/bright_green]"
                discount = coin.presale_discount or "TBA"
                highlights = ", ".join(coin.investment_highlights[:2])
                
                table.add_row(
                    coin.symbol,
                    coin.name,
                    score_str,
                    coin.launch_date or "TBA",
                    discount,
                    highlights
                )
            
            self.console.print(table)
            self.console.print()
    
    def show_trending_coins(self):
        """Display trending coins with positive momentum"""
        trending = self.analyzer.get_trending_coins()[:15]  # Show more trending coins
        if trending:
            self.console.print("[bold green]📊 LOW CAP CRYPTOCURRENCY OPPORTUNITIES[/bold green]\n")
            table = self.create_coin_table(trending, "� Low Cap Gems & Market Movers", show_rank=False)
            self.console.print(table)
            self.console.print()
        else:
            # If no trending coins, show top coins by score
            top_coins = self.analyzer.get_top_coins(15)
            self.console.print("[bold green]📊 LOW CAP CRYPTOCURRENCY OPPORTUNITIES[/bold green]\n")
            table = self.create_coin_table(top_coins, "� Low Cap Investment Opportunities", show_rank=False)
            self.console.print(table)
            self.console.print()
    
    def show_low_risk_options(self):
        """Display established, lower-risk options"""
        low_risk = self.analyzer.get_low_risk_coins()
        if low_risk:
            self.console.print("[bold cyan]🛡️ ESTABLISHED COINS (LOWER RISK)[/bold cyan]\n")
            table = self.create_coin_table(low_risk, "💼 Blue Chip Cryptos", show_rank=True)
            self.console.print(table)
            self.console.print()
    
    def show_summary_stats(self):
        """Display summary statistics"""
        total_coins = len(self.analyzer.coins)
        current_coins = len(self.analyzer.filter_by_status(CoinStatus.CURRENT))
        upcoming_coins = len(self.analyzer.filter_by_status(CoinStatus.UPCOMING))
        new_coins = len(self.analyzer.filter_by_status(CoinStatus.NEW))
        high_potential = len(self.analyzer.get_high_potential_coins())
        
        stats_text = f"""
[bold]📊 PORTFOLIO SUMMARY[/bold]

• Total Coins Analyzed: [cyan]{total_coins}[/cyan]
• Current Trading: [green]{current_coins}[/green]
• Upcoming Launches: [yellow]{upcoming_coins}[/yellow]
• New Entries: [magenta]{new_coins}[/magenta]
• High Potential (8.0+ Score): [bright_green]{high_potential}[/bright_green]
        """
        
        panel = Panel(stats_text.strip(), box=box.ROUNDED, style="blue")
        self.console.print(panel)
        self.console.print()
    
    def show_interactive_menu(self):
        """Show interactive menu options"""
        menu_text = """
[bold yellow]🎯 QUICK ACTIONS[/bold yellow]

[cyan]1.[/cyan] View All Coins by Score
[cyan]2.[/cyan] Filter by Status (Current/New/Upcoming)  
[cyan]3.[/cyan] Show High Potential Coins (8.0+ Score)
[cyan]4.[/cyan] Refresh Local Data
[cyan]5.[/cyan] Fetch Live Data from CoinGecko
[cyan]6.[/cyan] Exit

[dim]Enter your choice (1-6):[/dim]
        """
        
        self.console.print(menu_text.strip())
    
    def run_full_analysis(self):
        """Run complete analysis display"""
        self.show_header()
        self.show_trending_coins()
    
    def run_interactive(self):
        """Run interactive mode"""
        while True:
            self.show_interactive_menu()
            try:
                choice = input().strip()
                self.console.clear()
                
                if choice == "1":
                    self.show_all_coins()
                elif choice == "2":
                    self.filter_by_status_menu()
                elif choice == "3":
                    self.show_high_potential()
                elif choice == "4":
                    self.analyzer.load_data()
                    self.console.print("[green]✅ Local data refreshed![/green]\n")
                elif choice == "5":
                    self.fetch_live_data_interactive()
                elif choice == "6":
                    self.console.print("[yellow]👋 Thanks for using Crypto Analyzer![/yellow]")
                    break
                else:
                    self.console.print("[red]❌ Invalid choice. Please try again.[/red]\n")
                    
                input("\nPress Enter to continue...")
                self.console.clear()
                
            except KeyboardInterrupt:
                self.console.print("\n[yellow]👋 Goodbye![/yellow]")
                break
    
    def show_all_coins(self):
        """Show all coins sorted by score"""
        all_coins = self.analyzer.get_top_coins(len(self.analyzer.coins))
        table = self.create_coin_table(all_coins, "🌟 All Coins by Attractiveness Score")
        self.console.print(table)
    
    def show_high_potential(self):
        """Show high potential coins"""
        high_potential = self.analyzer.get_high_potential_coins()
        if high_potential:
            table = self.create_coin_table(high_potential, "💎 High Potential Coins (8.0+ Score)")
            self.console.print(table)
        else:
            self.console.print("[yellow]No high potential coins found (8.0+ score)[/yellow]")
    
    def filter_by_status_menu(self):
        """Show coins filtered by status"""
        self.console.print("[bold]Filter by Status:[/bold]")
        self.console.print("1. Current Coins")
        self.console.print("2. New Coins") 
        self.console.print("3. Upcoming Coins")
        
        choice = input("Enter choice (1-3): ").strip()
        
        if choice == "1":
            coins = self.analyzer.filter_by_status(CoinStatus.CURRENT)
            title = "💰 Current Trading Coins"
        elif choice == "2":
            coins = self.analyzer.filter_by_status(CoinStatus.NEW)
            title = "🆕 New Market Entries"
        elif choice == "3":
            coins = self.analyzer.filter_by_status(CoinStatus.UPCOMING)
            title = "🔮 Upcoming Launches"
        else:
            self.console.print("[red]Invalid choice[/red]")
            return
        
        if coins:
            # Sort by attractiveness score
            coins = sorted(coins, key=lambda x: x.attractiveness_score, reverse=True)
            table = self.create_coin_table(coins, title)
            self.console.print(table)
        else:
            self.console.print(f"[yellow]No coins found for this status[/yellow]")
    
    def fetch_live_data_interactive(self):
        """Fetch live data in interactive mode"""
        try:
            self.console.print("[yellow]🌐 Fetching live data from CoinGecko...[/yellow]")
            
            # Import here to avoid circular imports
            from live_data_fetcher import fetch_and_update_data
            
            live_data = fetch_and_update_data()
            if live_data:
                # Reload the analyzer with new data
                self.analyzer.load_data()
                self.console.print("[green]✅ Live data fetched and updated successfully![/green]")
                self.console.print(f"[dim]Loaded {len(self.analyzer.coins)} coins from live sources[/dim]\n")
            else:
                self.console.print("[red]❌ Failed to fetch live data. Using existing data.[/red]\n")
                
        except Exception as e:
            self.console.print(f"[red]❌ Error fetching live data: {e}[/red]\n")
    
    def show_visualizations(self):
        """Display ASCII charts and visualizations"""
        self.console.print("[bold purple]📊 DATA VISUALIZATIONS[/bold purple]\n")
        
        # Show attractiveness score chart
        top_coins = self.analyzer.get_top_coins(8)
        score_chart = self.visualizer.create_score_chart(top_coins)
        score_panel = Panel(score_chart, title="Attractiveness Scores", box=box.ROUNDED)
        self.console.print(score_panel)
        self.console.print()
        
        # Show price change chart
        price_chart = self.visualizer.create_price_change_chart(self.analyzer.coins)
        price_panel = Panel(price_chart, title="24-Hour Price Changes", box=box.ROUNDED)
        self.console.print(price_panel)
        self.console.print()
        
        # Show status distribution
        status_chart = self.visualizer.create_status_distribution(self.analyzer.coins)
        status_panel = Panel(status_chart, title="Portfolio Distribution", box=box.ROUNDED)
        self.console.print(status_panel)
        self.console.print()
        
        # Show market cap rankings
        ranking_chart = self.visualizer.create_market_cap_ranking(self.analyzer.coins)
        ranking_panel = Panel(ranking_chart, title="Market Cap Rankings", box=box.ROUNDED)
        self.console.print(ranking_panel)