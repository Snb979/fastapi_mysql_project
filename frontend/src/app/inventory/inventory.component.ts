import { Component, OnInit, OnDestroy } from '@angular/core';
import { ApiService } from '../core/api.service';
import { Subject } from 'rxjs';

interface SheetInfo {
  name: string;
  rows: number;
  columns: string[];
  is_valid: boolean;
  errors: string[];
}

interface PreviewRow {
  temp_id: number;
  name: string;
  description: string;
  price: number;
  quantity: number;
  id?: number;
  [key: string]: any;
}

interface UploadProgress {
  type: string;
  step: string;
  progress: number;
  message: string;
  data?: any;
}

@Component({
  selector: 'app-inventory',
  templateUrl: './inventory.component.html',
  styleUrls: ['./inventory.component.scss']
})
export class InventoryComponent implements OnInit, OnDestroy {
  items: any[] = []; // Lista completa de productos
  filteredItems: any[] = []; // Lista filtrada (búsqueda)
  paginatedItems: any[] = []; // Lista visible por página
  newItem = { name: '', description: '', price: 0, quantity: 0 };

  // 🔹 Paginación
  currentPage = 1;
  itemsPerPage = 5;

  // 🔹 Búsqueda
  searchTerm = '';

  private destroy$ = new Subject<void>();
  private ws: WebSocket | null = null;
  private wsUrl = 'ws://localhost:8000/ws/upload';

  // Estado del modal
  showExcelModal = false;

  // Archivo
  selectedFile: File | null = null;
  fileName: string = '';
  fileSize: number = 0;

  // Análisis de hojas
  sheets: SheetInfo[] = [];
  selectedSheet: string = '';
  showSheetSelector: boolean = false;

  // Vista previa
  showPreview: boolean = false;
  previewData: PreviewRow[] = [];
  originalPreviewData: PreviewRow[] = [];
  totalRows: number = 0;
  columns: string[] = [];

  // Edición
  editingRow: PreviewRow | null = null;
  editingRowCopy: PreviewRow | null = null;

  // Progreso
  isUploading: boolean = false;
  uploadProgress: number = 0;
  uploadMessage: string = '';
  uploadStep: string = '';
  uploadStats = {
    created: 0,
    updated: 0,
    errors: 0
  };

  // Errores
  errors: string[] = [];
  showErrorDialog: boolean = false;
  generalError: string = '';

  constructor(private api: ApiService) { }

  ngOnInit() {
    this.loadItems(); // Cargar productos al iniciar la página
    this.connectWebSocket();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
    this.closeWebSocket();
  }

  // Cargar todos los productos desde el backend
  loadItems() {
    this.api.getItems().subscribe({
      next: (response: any) => {
        console.log('Respuesta del backend:', response);
        this.items = response.data || [];
        this.filteredItems = [...this.items];
        this.updatePaginatedItems(); // Inicializa la primera página
      },
      error: (error) => {
        console.error('Error al cargar productos:', error);
        this.items = [];
        this.filteredItems = [];
        this.paginatedItems = [];
      }
    });
  }

  // Agregar un nuevo producto
  addItem() {
    if (!this.newItem.name || !this.newItem.description) return;
    this.api.addItem(this.newItem).subscribe({
      next: () => {
        this.newItem = { name: '', description: '', price: 0, quantity: 0 };
        this.loadItems();
        this.currentPage = 1;
      },
      error: (error) => {
        console.error('Error al agregar producto:', error);
      }
    });
  }

  // Eliminar un producto
  deleteItem(id: number) {
    this.api.deleteItem(id).subscribe({
      next: () => {
        this.loadItems();
        this.currentPage = 1;
      },
      error: (error) => {
        console.error('Error al eliminar producto:', error);
      }
    });
  }

  // Filtro de búsqueda
  applyFilter(): void {
    const term = (this.searchTerm || '').toLowerCase().trim();

    if (!term) {
      this.filteredItems = [...this.items];
    } else {
      this.filteredItems = this.items.filter(item =>
        (item.name || '').toLowerCase().includes(term) ||
        (item.description || '').toLowerCase().includes(term)
      );
    }

    this.currentPage = 1;
    this.updatePaginatedItems();
  }

  // Actualizar los ítems visibles según la página actual
  updatePaginatedItems() {
    const start = (this.currentPage - 1) * this.itemsPerPage;
    const end = start + this.itemsPerPage;
    this.paginatedItems = this.filteredItems.slice(start, end);
  }

  // Paginación
  totalPages() {
    return Math.ceil(this.filteredItems.length / this.itemsPerPage);
  }

  nextPage() {
    if (this.currentPage < this.totalPages()) {
      this.currentPage++;
      this.updatePaginatedItems();
    }
  }

  prevPage() {
    if (this.currentPage > 1) {
      this.currentPage--;
      this.updatePaginatedItems();
    }
  }

  goToPage(page: number) {
    if (page >= 1 && page <= this.totalPages()) {
      this.currentPage = page;
      this.updatePaginatedItems();
    }
  }

  // ========================================
  // Carga de Excel
  // ========================================
  openExcelUploader() {
    this.showExcelModal = true;
    this.resetUploadState();
  }

  closeExcelModal() {
    this.showExcelModal = false;
    this.resetUploadState();
  }

  // ========== WEBSOCKET ==========

  connectWebSocket(): void {
    try {
      this.ws = new WebSocket(this.wsUrl);

      this.ws.onopen = () => {
        console.log('✓ WebSocket conectado');
      };

      this.ws.onmessage = (event) => {
        const data: UploadProgress = JSON.parse(event.data);
        this.handleWebSocketMessage(data);
      };

      this.ws.onerror = (error) => {
        console.error('Error en WebSocket:', error);
      };

      this.ws.onclose = () => {
        console.log('✗ WebSocket desconectado');
        setTimeout(() => {
          if (!this.isUploading) {
            this.connectWebSocket();
          }
        }, 3000);
      };
    } catch (error) {
      console.error('Error conectando WebSocket:', error);
    }
  }

  closeWebSocket(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  handleWebSocketMessage(data: UploadProgress): void {
    this.uploadProgress = data.progress;
    this.uploadMessage = data.message;
    this.uploadStep = data.step;

    if (data.data) {
      this.uploadStats = {
        created: data.data.created || 0,
        updated: data.data.updated || 0,
        errors: data.data.errors_count || data.data.errors || 0
      };

      if (data.data.errors && Array.isArray(data.data.errors)) {
        this.errors = data.data.errors;
      }
    }

    if (data.type === 'complete') {
      this.isUploading = false;
      this.showPreview = false;
      if (this.errors.length > 0) {
        this.showErrorDialog = true;
      }

      // Recargar la lista de productos
      this.loadItems();

      // Cerrar modal después de 3 segundos
      setTimeout(() => {
        if (this.errors.length === 0) {
          this.closeExcelModal();
        }
      }, 3000);
    }

    if (data.type === 'error') {
      this.isUploading = false;
      this.showError(data.message);
    }
  }

  // ========== MANEJO DE ARCHIVO ==========

  onFileSelected(event: any): void {
    const file = event.target.files[0];
    if (!file) return;

    const validExtensions = ['.xls', '.xlsx'];
    const fileExtension = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();

    if (!validExtensions.includes(fileExtension)) {
      this.showError('Por favor selecciona un archivo Excel válido (.xls o .xlsx)');
      event.target.value = '';
      return;
    }

    const maxSize = 10 * 1024 * 1024;
    if (file.size > maxSize) {
      this.showError(`El archivo es demasiado grande (${(file.size / 1024 / 1024).toFixed(2)} MB). El límite es 10 MB.`);
      event.target.value = '';
      return;
    }

    this.selectedFile = file;
    this.fileName = file.name;
    this.fileSize = file.size;
    this.errors = [];
    this.generalError = '';

    this.analyzeFile();
  }

  analyzeFile(): void {
    if (!this.selectedFile) return;

    const formData = new FormData();
    formData.append('file', this.selectedFile);

    this.api.analyzeExcel(formData).subscribe({
      next: (response) => {
        if (response.success) {
          this.sheets = response.data.sheets;

          if (response.data.total_sheets > 1) {
            this.showSheetSelector = true;
            if (response.data.selected_sheet) {
              this.selectedSheet = response.data.selected_sheet;
              this.loadPreview();
            }
          } else if (response.data.total_sheets === 1) {
            const sheet = this.sheets[0];
            if (sheet.is_valid) {
              this.selectedSheet = sheet.name;
              this.loadPreview();
            } else {
              this.showError(`La hoja "${sheet.name}" tiene errores: ${sheet.errors.join(', ')}`);
            }
          }
        }
      },
      error: (error) => {
        this.handleError(error);
      }
    });
  }

  selectSheet(sheetName: string): void {
    const sheet = this.sheets.find(s => s.name === sheetName);

    if (sheet && !sheet.is_valid) {
      this.showError(`La hoja "${sheetName}" tiene errores: ${sheet.errors.join(', ')}`);
      return;
    }

    this.selectedSheet = sheetName;
    this.loadPreview();
  }

  loadPreview(): void {
    if (!this.selectedFile || !this.selectedSheet) return;

    const formData = new FormData();
    formData.append('file', this.selectedFile);

    this.api.previewExcel(formData, this.selectedSheet).subscribe({
      next: (response) => {
        if (response.success) {
          this.previewData = response.data.preview_rows;
          this.originalPreviewData = JSON.parse(JSON.stringify(response.data.preview_rows));
          this.totalRows = response.data.total_rows;
          this.columns = response.data.columns.filter((col: string) => col !== 'temp_id');
          this.showPreview = true;
          this.showSheetSelector = false;
        }
      },
      error: (error) => {
        this.handleError(error);
      }
    });
  }

  // ========== EDICIÓN ==========
  startEdit(row: PreviewRow): void {
    this.editingRow = row;
    this.editingRowCopy = { ...row };
  }

  cancelEdit(): void {
    if (this.editingRow && this.editingRowCopy) {
      Object.assign(this.editingRow, this.editingRowCopy);
    }
    this.editingRow = null;
    this.editingRowCopy = null;
  }

  saveEdit(): void {
    this.editingRow = null;
    this.editingRowCopy = null;
  }

  deleteRow(row: PreviewRow): void {
    const index = this.previewData.findIndex(r => r.temp_id === row.temp_id);
    if (index > -1) {
      this.previewData.splice(index, 1);
      this.totalRows--;
    }
  }

  // ========== CARGA ==========
  confirmUpload(): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      this.showError('No hay conexión con el servidor. Reintentando...');
      this.connectWebSocket();
      setTimeout(() => this.confirmUpload(), 1000);
      return;
    }

    this.isUploading = true;
    this.uploadProgress = 0;
    this.uploadMessage = 'Iniciando carga...';
    this.errors = [];
    this.uploadStats = { created: 0, updated: 0, errors: 0 };

    this.ws.send(JSON.stringify({
      action: 'start_upload',
      rows: this.previewData
    }));
  }

  cancelPreview(): void {
    this.showPreview = false;
    this.previewData = [];
    this.selectedSheet = '';
    if (this.sheets.length > 1) {
      this.showSheetSelector = true;
    } else {
      this.resetUploadState();
    }
  }

  // ========== UTILIDADES ==========

  resetUploadState(): void {
    this.selectedFile = null;
    this.fileName = '';
    this.fileSize = 0;
    this.sheets = [];
    this.selectedSheet = '';
    this.showSheetSelector = false;
    this.showPreview = false;
    this.previewData = [];
    this.originalPreviewData = [];
    this.totalRows = 0;
    this.columns = [];
    this.uploadProgress = 0;
    this.uploadMessage = '';
    this.uploadStats = { created: 0, updated: 0, errors: 0 };
    this.errors = [];
    this.generalError = '';
    this.isUploading = false;
  }

  showError(message: string): void {
    this.generalError = message;
    setTimeout(() => {
      this.generalError = '';
    }, 5000);
  }

  handleError(error: any): void {
    if (error.error && error.error.detail) {
      this.showError(error.error.detail);
    } else {
      this.showError('Ocurrió un error al procesar el archivo');
    }
  }

  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  }

  getProgressColor(): string {
    if (this.uploadProgress < 33) return '#3498db';
    if (this.uploadProgress < 66) return '#f39c12';
    if (this.uploadProgress < 100) return '#e74c3c';
    return '#27ae60';
  }

  closeErrorDialog(): void {
    this.showErrorDialog = false;
  }
}
