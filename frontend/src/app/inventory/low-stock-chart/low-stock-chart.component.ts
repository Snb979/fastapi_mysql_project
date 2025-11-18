import { Component, OnInit, ViewChild, ElementRef, OnDestroy } from '@angular/core';
import { Chart, registerables } from 'chart.js';
import { HttpClient } from '@angular/common/http';

Chart.register(...registerables);

@Component({
  selector: 'app-low-stock-chart',
  templateUrl: './low-stock-chart.component.html',
  styleUrls: ['./low-stock-chart.component.scss']
})
export class LowStockChartComponent implements OnInit, OnDestroy {
  
  @ViewChild('chartCanvas') chartCanvas!: ElementRef<HTMLCanvasElement>;
  
  chart: Chart | null = null;
  loading = true;
  error = '';
  noData = false;
  productCount = 0;

  private apiUrl = 'http://localhost:8000';

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    this.loadLowStockProducts();
  }

  loadLowStockProducts(): void {
    this.loading = true;
    this.error = '';
    
    this.http.get<any>(`${this.apiUrl}/products/low-stock?threshold=10`).subscribe({
      next: (result) => {
        if (result.data && result.data.length > 0) {
          const sortedProducts = result.data.sort((a: any, b: any) => a.quantity - b.quantity);
          
          const labels = sortedProducts.map((p: any) => p.name);
          const quantities = sortedProducts.map((p: any) => p.quantity);
          
          this.productCount = sortedProducts.length;
          this.noData = false;
          
          setTimeout(() => {
            this.createChart(labels, quantities);
          }, 100);
        } else {
          this.noData = true;
        }
        this.loading = false;
      },
      error: (err) => {
        console.error('Error cargando productos:', err);
        this.error = 'Error al cargar los datos del gráfico';
        this.loading = false;
      }
    });
  }

  createChart(labels: string[], data: number[]): void {
    if (this.chart) {
      this.chart.destroy();
    }

    const canvas = this.chartCanvas?.nativeElement;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    this.chart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Stock Actual',
          data: data,
          backgroundColor: 'rgba(239, 68, 68, 0.7)',
          borderColor: 'rgba(239, 68, 68, 1)',
          borderWidth: 2,
          hoverBackgroundColor: 'rgba(239, 68, 68, 0.9)'
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: true,
            position: 'top'
          },
          title: {
            display: true,
            text: '⚠️ Productos con Bajo Stock (menos de 10 unidades)',
            font: {
              size: 18,
              weight: 'bold'
            }
          },
          tooltip: {
            callbacks: {
              label: (context) => {
                return `Stock: ${context.parsed.x} unidades`;
              }
            }
          }
        },
        scales: {
          x: {
            beginAtZero: true,
            title: {
              display: true,
              text: 'Cantidad en Stock'
            },
            ticks: {
              stepSize: 1
            }
          },
          y: {
            title: {
              display: true,
              text: 'Productos'
            }
          }
        }
      }
    });
  }

  reloadData(): void {
    this.loadLowStockProducts();
  }

  ngOnDestroy(): void {
    if (this.chart) {
      this.chart.destroy();
    }
  }
}