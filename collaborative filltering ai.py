from flask import Flask, jsonify, request
import mysql.connector
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict

app = Flask(__name__)

def connect_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="dbkaliansendiri"
    )

def get_transaction_data():
    """Mengambil data transaksi dan mengelompokkan produk berdasarkan invoice"""
    db = connect_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT transaksi_invoice, transaksi_produk FROM transaksi")
    transactions = cursor.fetchall()
    db.close()
    
    invoice_dict = defaultdict(set)
    for trans in transactions:
        invoice_dict[trans['transaksi_invoice']].add(trans['transaksi_produk'])
    
    return list(invoice_dict.values())

def build_similarity_matrix():
    """Membangun matriks kesamaan produk berdasarkan transaksi"""
    transactions = get_transaction_data()
    
    all_products = list(set(prod for transaction in transactions for prod in transaction))
    product_index = {prod: i for i, prod in enumerate(all_products)}
    
    matrix = np.zeros((len(all_products), len(all_products)))
    
    for transaction in transactions:
        indices = [product_index[prod] for prod in transaction]
        for i in indices:
            for j in indices:
                if i != j:
                    matrix[i, j] += 1
    
    similarity_matrix = cosine_similarity(matrix)
    return similarity_matrix, product_index, all_products

def get_product_details(product_ids):
    """Mengambil detail produk berdasarkan daftar ID"""
    if not product_ids:
        return []
    
    db = connect_db()
    cursor = db.cursor(dictionary=True)
    format_strings = ','.join(['%s'] * len(product_ids))
    query = f"SELECT * FROM produk WHERE produk_id IN ({format_strings})"
    cursor.execute(query, tuple(product_ids))
    products = cursor.fetchall()
    db.close()
    
    return products

def get_recommendations(produk_id):
    """Mengembalikan rekomendasi berdasarkan pola transaksi"""
    similarity_matrix, product_index, all_products = build_similarity_matrix()
    
    if produk_id not in product_index:
        return []
    
    idx = product_index[produk_id]
    similarity_scores = similarity_matrix[idx]
    
    recommended_indices = np.argsort(similarity_scores)[::-1][1:6]  # ini akan mengambil 5 data teratas dari produk kalian
    recommended_products = [all_products[i] for i in recommended_indices]
    
    return get_product_details(recommended_products)

@app.route('/rekomendasi', methods=['GET'])
def rekomendasi_produk():
    produk_id = request.args.get('produk_id', type=int)
    
    if not produk_id:
        return jsonify({"error": "produk_id diperlukan"}), 400
    
    rekomendasi = get_recommendations(produk_id)
    
    if not rekomendasi:
        return jsonify({"error": "Tidak ada rekomendasi yang ditemukan"}), 404
    
    return jsonify({"rekomendasi": rekomendasi})

if __name__ == '__main__':
    app.run(debug=True)
