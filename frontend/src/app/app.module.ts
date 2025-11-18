import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { FormsModule } from '@angular/forms';
import { HttpClientModule } from '@angular/common/http';
import { HighStockChartComponent } from './inventory/high-stock-chart/high-stock-chart.component';
import { AppComponent } from './app.component';
import { InventoryComponent } from './inventory/inventory.component';
import { LowStockChartComponent } from './inventory/low-stock-chart/low-stock-chart.component';



@NgModule({
  declarations: [
    AppComponent,
    InventoryComponent,
    LowStockChartComponent,
    HighStockChartComponent
  ],
  imports: [
    BrowserModule, 
    FormsModule, 
    HttpClientModule
  ],
  providers: [],
  bootstrap: [AppComponent]
})
export class AppModule {}