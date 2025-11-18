import { ComponentFixture, TestBed } from '@angular/core/testing';

import { LowStockChartComponent } from './low-stock-chart.component';

describe('LowStockChartComponent', () => {
  let component: LowStockChartComponent;
  let fixture: ComponentFixture<LowStockChartComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ LowStockChartComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(LowStockChartComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
