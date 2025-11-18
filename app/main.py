# Importaciones necesarias
import io
import json
import asyncio
import pandas as pd 
import openpyxl
from typing import List, Dict, Any
from fastapi.middleware.cors import CORSMiddleware
from database import SessionLocal, engine, Base
from models import Product
from utils.response import build_response
from schemas import ProductCreate, ProductOut
from fastapi.responses import JSONResponse
from fastapi import FastAPI, Depends, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from sqlalchemy.orm import Session as OrmSession
from crud import (
    create_product,
    get_products,
    get_product_by_id,
    update_product,
    delete_product,
    filter_products_by_price
)
from utils.validators import (
    validate_name,
    validate_price,
    validate_quantity,
    validate_description
)

# Crear tablas en la base de datos
Base.metadata.create_all(bind=engine)

# Inicializar la app FastAPI
app = FastAPI()

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependencia para obtener sesión de base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Crear producto
@app.post("/products/", response_model=dict)
def create_product_endpoint(product: ProductCreate, db: Session = Depends(get_db)):
    try:
        # Validaciones
        if not validate_name(product.name):
            raise ValueError("El nombre no puede estar vacío")

        if not validate_price(product.price):
            raise ValueError("El precio debe ser cero o mayor")

        if not validate_quantity(product.quantity):
            raise ValueError("La cantidad debe ser cero o mayor")

        if not validate_description(product.description):
            raise ValueError("La descripción no puede estar vacía")

        new_product = create_product(db, product)
        return build_response(
            status=201,
            type_="success",
            title="Producto creado",
            message="El producto fue creado correctamente",
            data=ProductOut.from_orm(new_product)
        )
    except Exception as e:
        return build_response(
            status=500,
            type_="error",
            title="Error al crear producto",
            message="No se pudo crear el producto",
            error=str(e)
        )

# Listar productos
@app.get("/products/", response_model=dict)
def list_products(db: Session = Depends(get_db)):
    try:
        products = get_products(db)
        serialized = [ProductOut.from_orm(p) for p in products]
        return build_response(
            title="Listado de productos",
            message="Productos obtenidos correctamente",
            data=serialized
        )
    except Exception as e:
        return build_response(
            type_="error",
            title="Error al obtener productos",
            message="No se pudo obtener el listado",
            error=str(e)
        )

# Filtrar productos por precio mínimo
@app.get("/products/filter", response_model=dict)
def filter_products(min_price: float, db: Session = Depends(get_db)):
    try:
        filtered = filter_products_by_price(db, min_price)
        serialized = [ProductOut.from_orm(p) for p in filtered]
        return build_response(
            title="Productos filtrados",
            message="Productos filtrados correctamente",
            data=serialized
        )
    except Exception as e:
        return build_response(
            type_="error",
            title="Error al filtrar productos",
            message="No se pudo filtrar productos",
            error=str(e)
        )
@app.get("/products/low-stock", response_model=dict)
def get_low_stock_products(threshold: int = 10, db: Session = Depends(get_db)):
    """
    Obtiene productos con stock bajo (por defecto menos de 10 unidades)
    """
    try:
        products = db.query(Product).filter(Product.quantity < threshold).order_by(Product.quantity.asc()).all()
        serialized = [ProductOut.from_orm(p) for p in products]
        return build_response(
            title="Productos con bajo stock",
            message=f"Se encontraron {len(products)} productos con menos de {threshold} unidades",
            data=serialized
        )
    except Exception as e:
        return build_response(
            type_="error",
            title="Error al obtener productos",
            message="No se pudo obtener el listado",
            error=str(e)
        )
        
@app.get("/products/high-stock", response_model=dict)
def get_high_stock_products(limit: int = 5, db: Session = Depends(get_db)):
    """
    Obtiene los productos con mayor stock
    """
    try:
        products = db.query(Product).order_by(Product.quantity.desc()).limit(limit).all()
        serialized = [ProductOut.from_orm(p) for p in products]
        return build_response(
            title="Productos con mayor stock",
            message=f"Se encontraron {len(products)} productos con mayor cantidad",
            data=serialized
        )
    except Exception as e:
        return build_response(
            type_="error",
            title="Error al obtener productos",
            message="No se pudo obtener el listado",
            error=str(e)
        )
# Obtener producto por ID
@app.get("/products/{product_id}", response_model=dict)
def read_product(product_id: int, db: Session = Depends(get_db)):
    try:
        product = get_product_by_id(db, product_id)
        if not product:
            return build_response(
                status=404,
                type_="error",
                title="Producto no encontrado",
                message="No existe un producto con ese ID"
            )
        return build_response(
            title="Producto obtenido",
            message="Producto obtenido correctamente",
            data=ProductOut.from_orm(product)
        )
    except Exception as e:
        return build_response(
            type_="error",
            title="Error al obtener producto",
            message="No se pudo obtener el producto",
            error=str(e)
        )

# Actualizar producto
@app.put("/products/{product_id}", response_model=dict)
def update_product_endpoint(product_id: int, product_data: ProductCreate, db: Session = Depends(get_db)):
    try:
        # Validaciones
        if not validate_name(product_data.name):
            raise ValueError("El nombre no puede estar vacío")

        if not validate_price(product_data.price):
            raise ValueError("El precio debe ser cero o mayor")

        if not validate_quantity(product_data.quantity):
            raise ValueError("La cantidad debe ser cero o mayor")

        if not validate_description(product_data.description):
            raise ValueError("La descripción no puede estar vacía")

        updated = update_product(db, product_id, product_data)
        if not updated:
            return build_response(
                status=404,
                type_="error",
                title="Producto no encontrado",
                message="No existe un producto con ese ID"
            )
        return build_response(
            title="Producto actualizado",
            message="Producto actualizado correctamente",
            data=ProductOut.from_orm(updated)
        )
    except Exception as e:
        return build_response(
            type_="error",
            title="Error al actualizar producto",
            message="No se pudo actualizar el producto",
            error=str(e)
        )

# Eliminar producto
@app.delete("/products/{product_id}", response_model=dict)
def delete_product_endpoint(product_id: int, db: Session = Depends(get_db)):
    try:
        deleted = delete_product(db, product_id)
        if not deleted:
            return build_response(
                status=404,
                type_="error",
                title="Producto no encontrado",
                message="No existe un producto con ese ID"
            )
        return build_response(
            title="Producto eliminado",
            message="Producto eliminado correctamente",
            data=True
        )
    except Exception as e:
        return build_response(
            type_="error",
            title="Error al eliminar producto",
            message="No se pudo eliminar el producto",
            error=str(e)
        )
        
        
class ConnectionManager:
    """Gestiona las conexiones WebSocket activas"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        """Acepta y registra una nueva conexión"""
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"✓ WebSocket conectado. Total conexiones: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Elimina una conexión cuando se desconecta"""
        self.active_connections.remove(websocket)
        print(f"✗ WebSocket desconectado. Total conexiones: {len(self.active_connections)}")
                
    async def send_message(self, websocket: WebSocket, message: Dict[str, Any]):
        """Alias compatible para evitar errores en código anterior"""
        await websocket.send_json(message)

# Instancia global del gestor
manager = ConnectionManager()

def is_number(value):
    try:
        float(str(value).replace(",", "."))
        return True
    except:
        return False

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r'\s+', '_', regex=True)
    )
    return df

def validate_sheet(df: pd.DataFrame, sheet_name: str) -> Dict[str, Any]:
    """Valida una hoja de Excel"""
    errors = []
    required_columns = {"name", "description", "price", "quantity"}
    
    # Normalizar columnas
    df = normalize_columns(df)
    
    # Verificar columnas requeridas
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        errors.append(f"Faltan columnas requeridas: {', '.join(missing_columns)}")
    
    # Verificar filas vacías
    if df.empty:
        errors.append("La hoja está vacía")
    
    if 'price' in df.columns:
        non_numeric_prices = df[~df['price'].apply(is_number)]
        if not non_numeric_prices.empty:
            errors.append(f"Hay {len(non_numeric_prices)} filas con precios inválidos")

    if 'quantity' in df.columns:
        # Convertir a string de forma segura antes de validar
        non_numeric_qty = df[~df['quantity'].astype(str).str.isdigit()]
        if not non_numeric_qty.empty:
            errors.append(f"Hay {len(non_numeric_qty)} filas con cantidades inválidas")
    
    return {
        "name": sheet_name,
        "rows": len(df),
        "columns": list(df.columns),
        "is_valid": len(errors) == 0,
        "errors": errors
    }
    
def process_excel_file(contents: bytes) -> Dict[str, Any]:
    """Procesa archivo Excel y retorna información de hojas"""
    try:
        excel_file = io.BytesIO(contents)
        excel_data = pd.ExcelFile(excel_file, engine='openpyxl')
        
        sheets_info = []
        valid_sheets = []
        
        for sheet_name in excel_data.sheet_names:
            df = pd.read_excel(excel_data, sheet_name=sheet_name)
            validation = validate_sheet(df, sheet_name)
            sheets_info.append(validation)
            
            if validation['is_valid']:
                valid_sheets.append(sheet_name)
        
        # Si solo hay una hoja válida, seleccionarla automáticamente
        selected_sheet = valid_sheets[0] if len(valid_sheets) == 1 else None
        
        return {
            "sheets": sheets_info,
            "selected_sheet": selected_sheet,
            "total_sheets": len(excel_data.sheet_names),
            "valid_sheets": valid_sheets
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error procesando Excel: {str(e)}")

@app.post("/upload-excel/analyze")
async def analyze_excel(file: UploadFile = File(...)):
    """Analiza el archivo Excel y retorna información de las hojas"""
    
    # Validar extensión
    if not file.filename.endswith(('.xls', '.xlsx')):
        raise HTTPException(status_code=400, detail="El archivo debe ser .xls o .xlsx")
    
    # Validar tamaño (10MB)
    contents = await file.read()
    max_size = 10 * 1024 * 1024
    file_size_mb = len(contents) / (1024 * 1024)
    
    if len(contents) > max_size:
        raise HTTPException(
            status_code=400, 
            detail=f"El archivo excede el límite de 10 MB (tamaño: {file_size_mb:.2f} MB)"
        )
    
    # Procesar y analizar hojas
    analysis = process_excel_file(contents)
    
    return {
        "success": True,
        "data": analysis,
        "file_size_mb": round(file_size_mb, 2)
    }

@app.post("/upload-excel/preview")
async def preview_excel(file: UploadFile = File(...), sheet_name: str = None):
    """Genera vista previa de la hoja seleccionada"""
    
    contents = await file.read()
    excel_file = io.BytesIO(contents)
    
    try:
        # Si no se especifica hoja, usar la primera
        if sheet_name:
            df = pd.read_excel(excel_file, sheet_name=sheet_name, engine='openpyxl')
        else:
            df = pd.read_excel(excel_file, engine='openpyxl')
        
        # Normalizar columnas
        df = normalize_columns(df)
        
        # Agregar ID temporal para referencia
        df.insert(0, 'temp_id', range(1, len(df) + 1))
        
        # Convertir a formato JSON serializable
        preview_data = df.head(100).to_dict('records')  # Mostrar primeras 100 filas
        
        # Limpiar valores NaN
        for row in preview_data:
            for key, value in row.items():
                if pd.isna(value):
                    row[key] = None
        
        return {
            "success": True,
            "data": {
                "preview_rows": preview_data,
                "total_rows": len(df),
                "columns": list(df.columns)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error generando vista previa: {str(e)}")
    
    
@app.post("/upload-excel/validate-duplicates")
async def validate_duplicates(file: UploadFile = File(...), sheet_name: str = None, db: Session = Depends(get_db)):
    print("🔍 VALIDACIÓN DE DUPLICADOS INICIADA")
    
    contents = await file.read()
    excel_file = io.BytesIO(contents)
    
    try:
        if sheet_name:
            df = pd.read_excel(excel_file, sheet_name=sheet_name, engine='openpyxl')
        else:
            df = pd.read_excel(excel_file, engine='openpyxl')
        
        df = normalize_columns(df)
        df.insert(0, 'temp_id', range(1, len(df) + 1))
        
        # Obtener productos existentes en BD
        existing_products = db.query(Product).all()
        existing_names = {p.name.lower().strip(): p for p in existing_products}
        
        print(f"💾 Productos en BD: {len(existing_products)}")
        
        preview_data = []
        duplicates_found = 0
        new_products = 0
        
        # ⬇️ NUEVO: Rastrear nombres ya vistos en el Excel
        seen_in_excel = {}
        
        for idx, row in df.iterrows():
            row_dict = row.to_dict()
            
            for key, value in row_dict.items():
                if pd.isna(value):
                    row_dict[key] = None
            
            name = str(row_dict.get('name', '')).strip()
            name_lower = name.lower()
            
            # ⬇️ NUEVO: Verificar si es duplicado DENTRO del Excel
            if name_lower in seen_in_excel:
                row_dict['status'] = 'duplicate_excel'
                row_dict['status_label'] = 'Duplicado en Excel'
                row_dict['existing_id'] = None
                row_dict['duplicate_row'] = seen_in_excel[name_lower]
                duplicates_found += 1
                print(f"⚠️  DUPLICADO EN EXCEL: {name} (fila {seen_in_excel[name_lower] + 2})")
            
            # Verificar si es duplicado con la BD
            elif name_lower in existing_names:
                existing_product = existing_names[name_lower]
                row_dict['status'] = 'duplicate'
                row_dict['status_label'] = 'Duplicado en BD'
                row_dict['existing_id'] = existing_product.id
                duplicates_found += 1
                print(f"⚠️  DUPLICADO EN BD: {name}")
            
            # Es nuevo
            else:
                row_dict['status'] = 'new'
                row_dict['status_label'] = 'Nuevo'
                new_products += 1
                # Registrar este nombre como visto
                seen_in_excel[name_lower] = idx
            
            preview_data.append(row_dict)
        
        print(f"📊 Duplicados: {duplicates_found}, Nuevos: {new_products}")
        
        return {
            "success": True,
            "data": {
                "preview_rows": preview_data,
                "total_rows": len(df),
                "columns": list(df.columns),
                "duplicates_found": duplicates_found,
                "new_products": new_products,
                "has_duplicates": duplicates_found > 0
            }
        }
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")

# ========================================
# WEBSOCKET PARA CARGA EN TIEMPO REAL
# ========================================

@app.websocket("/ws/upload")
async def websocket_upload(websocket: WebSocket):
    await manager.connect(websocket)
    
    try:
        while True:
            # Recibir datos del cliente
            data = await websocket.receive_json()
            action = data.get('action')
            
            if action == 'start_upload':
                await process_upload(websocket, data)
            elif action == 'ping':
                await manager.send_message(websocket, {"type": "pong"})
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"Error en WebSocket: {e}")
        await manager.send_message(websocket, {
            "type": "error",
            "message": f"Error en la conexión: {str(e)}"
        })
        manager.disconnect(websocket)

async def process_upload(websocket: WebSocket, data: dict):
    """Procesa la carga de datos con validación de duplicados"""
    
    rows = data.get('rows', [])
    duplicate_action = data.get('duplicate_action', 'skip')  # skip, update, create_new
    total_rows = len(rows)
    
    if total_rows == 0:
        await manager.send_message(websocket, {
            "type": "error",
            "message": "No hay datos para procesar"
        })
        return
    
    db = SessionLocal()
    
    try:
        # Notificar inicio
        await manager.send_message(websocket, {
            "type": "progress",
            "step": "start",
            "progress": 0,
            "message": f"Iniciando carga de {total_rows} productos"
        })
        
        await asyncio.sleep(0.3)
        
        # Validación
        await manager.send_message(websocket, {
            "type": "progress",
            "step": "validating",
            "progress": 10,
            "message": "Validando datos y detectando duplicados..."
        })
        
        await asyncio.sleep(0.3)
        
        # Procesar por lotes
        batch_size = 10
        created = 0
        updated = 0
        skipped = 0
        errors = []
        
        for i in range(0, total_rows, batch_size):
            batch = rows[i:i + batch_size]
            
            for idx, row in enumerate(batch):
                try:
                    # Validaciones básicas
                    name = str(row.get('name', '')).strip()
                    description = str(row.get('description', '')).strip()
                    
                    if not name:
                        errors.append(f"Fila {i+idx+1}: Nombre vacío")
                        continue
                    
                    if not description:
                        errors.append(f"Fila {i+idx+1}: Descripción vacía")
                        continue
                    
                    try:
                        price = float(row.get('price', 0))
                        if price < 0:
                            errors.append(f"Fila {i+idx+1}: Precio negativo")
                            continue
                    except (ValueError, TypeError):
                        errors.append(f"Fila {i+idx+1}: Precio inválido")
                        continue
                    
                    try:
                        quantity = int(row.get('quantity', 0))
                        if quantity < 0:
                            errors.append(f"Fila {i+idx+1}: Cantidad negativa")
                            continue
                    except (ValueError, TypeError):
                        errors.append(f"Fila {i+idx+1}: Cantidad inválida")
                        continue
                    
                    # Verificar si es duplicado
                    existing_product = db.query(Product).filter(
                        Product.name.ilike(name)
                    ).first()
                    
                    if existing_product:
                        # Es un duplicado
                        if duplicate_action == 'skip':
                            skipped += 1
                            print(f"⊘ Producto duplicado saltado: {name}")
                            continue
                        
                        elif duplicate_action == 'update':
                            # Actualizar producto existente
                            existing_product.description = description
                            existing_product.price = price
                            existing_product.quantity = quantity
                            updated += 1
                            print(f"↻ Producto actualizado: {name}")
                        
                        elif duplicate_action == 'create_new':
                            # Crear como producto nuevo (aunque el nombre sea igual)
                            new_product = Product(
                                name=name,
                                description=description,
                                price=price,
                                quantity=quantity
                            )
                            db.add(new_product)
                            created += 1
                            print(f"+ Producto duplicado creado como nuevo: {name}")
                    else:
                        # Producto nuevo
                        new_product = Product(
                            name=name,
                            description=description,
                            price=price,
                            quantity=quantity
                        )
                        db.add(new_product)
                        created += 1
                        print(f"✓ Producto nuevo creado: {name}")
                    
                    # Commit cada 10 productos
                    if (created + updated) % 10 == 0:
                        db.commit()
                    
                except Exception as e:
                    errors.append(f"Fila {i+idx+1}: {str(e)}")
                    print(f"❌ Error en fila {i+idx+1}: {str(e)}")
                    continue
            
            # Commit del lote
            db.commit()
            
            # Notificar progreso
            progress = min(10 + int((i + batch_size) / total_rows * 80), 90)
            await manager.send_message(websocket, {
                "type": "progress",
                "step": "processing",
                "progress": progress,
                "message": f"Procesadas {min(i + batch_size, total_rows)} de {total_rows} filas",
                "data": {
                    "created": created,
                    "updated": updated,
                    "skipped": skipped,
                    "errors": len(errors)
                }
            })
        
        # Commit final
        db.commit()
        print(f"✅ Proceso completado: {created} creados, {updated} actualizados, {skipped} saltados")
        
        # Finalizar
        await manager.send_message(websocket, {
            "type": "progress",
            "step": "saving",
            "progress": 95,
            "message": "Guardando cambios..."
        })
        
        await asyncio.sleep(0.3)
        
        # Resultado final
        await manager.send_message(websocket, {
            "type": "complete",
            "step": "complete",
            "progress": 100,
            "message": "¡Carga completada exitosamente!",
            "data": {
                "total_rows": total_rows,
                "created": created,
                "updated": updated,
                "skipped": skipped,
                "errors_count": len(errors),
                "errors": errors[:10]
            }
        })
    
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {str(e)}")
        await manager.send_message(websocket, {
            "type": "error",
            "message": f"Error: {str(e)}"
        })
    
    
    finally:
        db.close()
        print("🔒 Sesión de base de datos cerrada")
      
# @app.websocket("/ws/upload-progress")
# async def websocket_endpoint(websocket: WebSocket):
#     await websocket.accept()
#     try:
#         while True:
#             data = await websocket.receive_text()
#             print(f"Mensaje recibido del cliente: {data}")
#             await websocket.send_json({"message": f"Mensaje recibido del cliente: {data}"})
#     except WebSocketDisconnect:
#         print("Cliente desconectado")

# ========================================
# ENDPOINT UPLOAD EXCEL CON NOTIFICACIONES WEBSOCKET
# ========================================

# @app.post("/upload-excel-ws/")
# async def upload_excel_websocket(file: UploadFile = File(...), db: Session = Depends(get_db)):
#     """
#     Endpoint para subir archivo Excel y enviar progreso vía WebSocket
#     """
    
#     async def send_update(step: str, progress: int, message: str, data: dict = None):
#         await manager.send_progress({
#             "step": step,
#             "progress": progress,
#             "message": message,
#             "data": data or {}
#         })
    
#     try:
#         await send_update("start", 0, f"Iniciando carga de {file.filename}")
        
#         # Validación extensión
#         if not file.filename.endswith(('.xls', '.xlsx')):
#             await send_update("error", 0, "Formato de archivo inválido")
#             raise HTTPException(status_code=400, detail="El archivo debe ser .xls o .xlsx")
#         await send_update("validation", 10, "Extensión válida")
        
#         # Validación tamaño
#         contents = await file.read()
#         max_size = 10 * 1024 * 1024
#         file_size_mb = len(contents) / (1024 * 1024)
#         if len(contents) > max_size:
#             await send_update("error", 0, f"Archivo demasiado grande: {file_size_mb:.2f} MB")
#             raise HTTPException(status_code=400, detail=f"El archivo supera el límite de 10 MB")
#         await send_update("validation", 20, f"Tamaño válido: {file_size_mb:.2f} MB")
        
#         # Leer Excel
#         try:
#             excel_data = io.BytesIO(contents)
#             df = pd.read_excel(excel_data, engine='openpyxl')
#             await send_update("reading", 30, f"Excel cargado: {len(df)} filas encontradas")
#         except Exception as e:
#             await send_update("error", 0, f"Error leyendo Excel: {str(e)}")
#             raise HTTPException(status_code=400, detail=f"Error leyendo archivo: {str(e)}")
        
#         # Normalizar columnas
#         df.columns = df.columns.str.strip().str.lower()
#         await send_update("processing", 40, "Columnas normalizadas")
        
#         # Verificar columnas requeridas
#         required_columns = {"name", "description", "price", "quantity"}
#         missing_columns = required_columns - set(df.columns)
#         if missing_columns:
#             await send_update("error", 0, f"Faltan columnas: {', '.join(missing_columns)}")
#             raise HTTPException(status_code=400, detail=f"Faltan columnas requeridas: {', '.join(missing_columns)}")
#         await send_update("processing", 50, "Estructura validada correctamente")
        
#         # Validar Excel vacío
#         if df.empty:
#             await send_update("error", 0, "El archivo Excel está vacío")
#             raise HTTPException(status_code=400, detail="El archivo Excel está vacío")
        
#         # Procesar filas con notificación de progreso
#         productos_creados = 0
#         productos_actualizados = 0
#         filas_con_error = []
#         total_filas = len(df)
        
#         for idx, row in df.iterrows():
#             progress = 50 + int((idx / total_filas) * 40)
#             try:
#                 data = row.to_dict()
#                 # Validaciones
#                 if pd.isna(data['name']) or str(data['name']).strip() == '':
#                     filas_con_error.append(f"Fila {idx + 2}: nombre vacío")
#                     continue
#                 if pd.isna(data['description']) or str(data['description']).strip() == '':
#                     filas_con_error.append(f"Fila {idx + 2}: descripción vacía")
#                     continue
#                 try:
#                     price = float(data['price'])
#                     if price < 0:
#                         filas_con_error.append(f"Fila {idx + 2}: precio negativo")
#                         continue
#                 except (ValueError, TypeError):
#                     filas_con_error.append(f"Fila {idx + 2}: precio inválido")
#                     continue
#                 try:
#                     quantity = int(data['quantity'])
#                     if quantity < 0:
#                         filas_con_error.append(f"Fila {idx + 2}: cantidad negativa")
#                         continue
#                 except (ValueError, TypeError):
#                     filas_con_error.append(f"Fila {idx + 2}: cantidad inválida")
#                     continue
                
#                 name = str(data['name']).strip()
#                 description = str(data['description']).strip()
                
#                 # Crear o actualizar producto
#                 if 'id' in data and pd.notna(data['id']):
#                     product_id = int(data['id'])
#                     product = db.query(Product).filter(Product.id == product_id).first()
#                     if product:
#                         product.name = name
#                         product.description = description
#                         product.price = price
#                         product.quantity = quantity
#                         productos_actualizados += 1
#                     else:
#                         nuevo = Product(name=name, description=description, price=price, quantity=quantity)
#                         db.add(nuevo)
#                         productos_creados += 1
#                 else:
#                     nuevo = Product(name=name, description=description, price=price, quantity=quantity)
#                     db.add(nuevo)
#                     productos_creados += 1
                
#                 # Enviar actualización cada 5 filas
#                 if (idx + 1) % 5 == 0:
#                     await send_update(
#                         "processing",
#                         progress,
#                         f"Procesando fila {idx + 1} de {total_filas}",
#                         {
#                             "creados": productos_creados,
#                             "actualizados": productos_actualizados,
#                             "errores": len(filas_con_error)
#                         }
#                     )
#             except Exception as e:
#                 filas_con_error.append(f"Fila {idx + 2}: {str(e)}")
#                 continue
        
#         await send_update("saving", 90, "Guardando cambios en la base de datos...")
#         db.commit()
        
#         response_data = {
#             "message": "Proceso completado exitosamente",
#             "total_filas": total_filas,
#             "productos_creados": productos_creados,
#             "productos_actualizados": productos_actualizados,
#             "filas_con_error": len(filas_con_error),
#             "errores": filas_con_error[:10] if filas_con_error else []
#         }
        
#         await send_update("complete", 100, "¡Carga completada!", response_data)
        
#         return JSONResponse(content=response_data)
    
#     except HTTPException as he:
#         raise he
#     except Exception as e:
#         await send_update("error", 0, f"Error inesperado: {str(e)}")
#         db.rollback()
#         raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# ========================================
# ENDPOINT DE PRUEBA WEBSOCKET
# ========================================

# @app.get("/test-ws")
# async def test_websocket():
#     """
#     Endpoint de prueba para verificar que WebSocket funciona
#     """
#     await manager.send_progress({
#         "step": "test",
#         "progress": 50,
#         "message": "Mensaje de prueba desde el servidor",
#         "data": {"timestamp": "2025-11-13"}
#     })
#     return {"message": "Mensaje de prueba enviado a todos los clientes conectados"}

@app.get("/")
async def root():
    return {"message": "Bienvenido a mi API"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
