import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private baseUrl = `${environment.apiUrl}/products`;
  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  getItems(): Observable<any> {
    return this.http.get(this.baseUrl);
  }

  addItem(item: any): Observable<any> {
    return this.http.post(this.baseUrl, item);
  }

  deleteItem(id: number): Observable<any> {
    return this.http.delete(`${this.baseUrl}/${id}`);
  }

  updateItem(id: number, item: any): Observable<any> {
    return this.http.put(`${this.baseUrl}/${id}`, item);
  }

  /**
   * Analiza el archivo Excel y retorna información de las hojas
   */
  analyzeExcel(formData: FormData): Observable<any> {
    return this.http.post(`${this.apiUrl}/upload-excel/analyze`, formData);
  }

  /**
   * Genera vista previa de una hoja específica del Excel
   */
  previewExcel(formData: FormData, sheetName: string): Observable<any> {
    return this.http.post(
      `${this.apiUrl}/upload-excel/preview?sheet_name=${encodeURIComponent(sheetName)}`, 
      formData
    );
  }

  /**
   * Carga masiva de productos desde Excel (sin WebSocket, para respaldo)
   */
  uploadExcel(formData: FormData): Observable<any> {
    return this.http.post(`${this.apiUrl}/upload-excel-ws/`, formData);
  }
}