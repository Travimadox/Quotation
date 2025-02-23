import streamlit as st
import pandas as pd
from datetime import datetime
import json
from fpdf import FPDF
import os
import glob
from PIL import Image
import io
import base64
import tempfile

class QuotePDF(FPDF):
    def __init__(self, company_info):
        super().__init__()
        self.company_info = company_info
        self.logo_path = None
        
        # Handle logo storage
        if company_info.get('logo'):
            self._store_logo(company_info['logo'])

    def _store_logo(self, logo_file):
        """Store logo in temporary file and return path"""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
                tmp.write(logo_file.getvalue())
                self.logo_path = tmp.name
        except Exception as e:
            st.error(f"Error processing logo: {str(e)}")

    def header(self):
        # Logo handling
        if self.logo_path and os.path.exists(self.logo_path):
            self.image(self.logo_path, 10, 8, 33)
            start_y = 25
        else:
            start_y = 8

        # Company info
        self.set_font('Arial', 'B', 12)
        self.set_xy(100, start_y)
        self.cell(0, 6, self.company_info.get('name', ''), 0, 1, 'R')
        self.set_font('Arial', '', 10)
        self.set_x(100)
        self.multi_cell(0, 5, 
                       f"{self.company_info.get('address', '')}\n"
                       f"Tel: {self.company_info.get('phone', '')}\n"
                       f"Email: {self.company_info.get('email', '')}", 
                       0, 'R')
        
        # Quotation title
        self.ln(20)
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'QUOTATION', 0, 1, 'C')

    def footer(self):
        self.set_y(-25)
        self.set_font('Arial', '', 8)
        self.cell(0, 5, self.company_info.get('footer_text', ''), 0, 1, 'C')
        self.cell(0, 5, f'Page {self.page_no()}', 0, 0, 'C')

def initialize_session_state():
    defaults = {
        'itemss': [],
        'quote_number': 1,
        'editing_index': None,
        'client_info': {
            'name': '',
            'phone': '',
            'email': '',
            'address': ''
        },
        'company_info': {
            'name': 'Ayub Obiene',
            'address': 'Uaso\\Nile Road Junction\nNairobi, Kenya',
            'phone': '+254 720 317 278\n +254 743 064 111',
            'email': 'ayubochieng11@gmail.com',
            'logo': None,
            'footer_text': 'Thank you for your business!',
            'theme_color': '#4A90E2'
        },
        'search_term': ''
    }
    
    for key in defaults:
        if key not in st.session_state:
            st.session_state[key] = defaults[key]

def validate_number_input(value):
    """Validate and convert to float"""
    try:
        return float(value)
    except ValueError:
        st.error("Please enter a valid number")
        raise

def add_item():
    try:
        item = {
            'description': st.session_state.description.strip(),
            'unit_cost': validate_number_input(st.session_state.unit_cost),
            'quantity': validate_number_input(st.session_state.quantity),
            'amount': validate_number_input(st.session_state.unit_cost) * validate_number_input(st.session_state.quantity)
        }
        #item['amount'] = item['unit_cost'] * item['quantity']
        
        if not item['description']:
            st.error("Description cannot be empty")
            return

        if st.session_state.editing_index is not None:
            st.session_state.itemss[st.session_state.editing_index] = item
            st.session_state.editing_index = None
        else:
            st.session_state.itemss.append(item)
            
        # Clear form fields
        st.session_state.description = ''
        st.session_state.unit_cost = 0.0
        st.session_state.quantity = 1.0
        
    except Exception as e:
        st.error(f"Error adding item: {str(e)}")

def edit_item(index):
    item = st.session_state.itemss[index]
    st.session_state.description = item['description']
    st.session_state.unit_cost = item['unit_cost']
    st.session_state.quantity = item['quantity']
    st.session_state.editing_index = index

def delete_item(index):
    try:
        del st.session_state.itemss[index]
    except IndexError:
        st.error("Item index out of range")

def clear_form():
    st.session_state.itemss = []
    st.session_state.client_info = {k: '' for k in st.session_state.client_info}
    #st.session_state.description = ''
    #st.session_state.unit_cost = 0.0
    #st.session_state.quantity = 1.0

def save_quotation():
    if not st.session_state.client_info.get('name'):
        st.error("Client name is required")
        return None, None

    try:
        quote_data = {
            'quote_number': f"{st.session_state.quote_number:06d}",
            'date': datetime.now().strftime("%d-%m-%Y"),
            'client_info': st.session_state.client_info,
            'items': st.session_state.itemss,
            'total': sum(item['amount'] for item in st.session_state.itemss),
            'company_info': st.session_state.company_info  # Save current company info
        }
        
        # Save to JSON
        json_filename = f"quotation_{quote_data['quote_number']}.json"
        with open(json_filename, 'w') as f:
            json.dump(quote_data, f, indent=4)
        
        # Generate PDF
        pdf = create_pdf(quote_data, st.session_state.company_info)
        pdf_filename = f"quotation_{quote_data['quote_number']}.pdf"
        pdf.output(pdf_filename)
        
        st.session_state.quote_number += 1
        return json_filename, pdf_filename
    
    except Exception as e:
        st.error(f"Error saving quotation: {str(e)}")
        return None, None

def create_pdf(quote_data, company_info):
    pdf = QuotePDF(company_info)
    pdf.add_page()
    
    # Quote details
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, f"Quote Number: {quote_data['quote_number']}", 0, 1)
    pdf.cell(0, 10, f"Date: {quote_data['date']}", 0, 1)
    
    # Client Information
    pdf.ln(5)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'CLIENT INFORMATION', 0, 1)
    pdf.set_font('Arial', '', 10)
    for key, value in quote_data['client_info'].items():
        if value:  # Skip empty fields
            pdf.cell(0, 10, f"{key.title()}: {value}", 0, 1)
    
    # Items Table
    pdf.ln(10)
    col_widths = [100, 30, 30, 30]
    headers = ['Description', 'Unit Cost', 'Quantity', 'Amount']
    
    # Table header with theme color
    pdf.set_fill_color(*hex_to_rgb(company_info['theme_color']))
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Arial', 'B', 10)
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 10, header, 1, 0, 'C', True)
    pdf.ln()
    
    # Table content
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', '', 10)
    for item in quote_data['items']:
        pdf.cell(col_widths[0], 10, item['description'][:50], 1)  # Limit description length
        pdf.cell(col_widths[1], 10, f"{item['unit_cost']:,.2f}", 1, 0, 'R')
        pdf.cell(col_widths[2], 10, f"{item['quantity']:,.2f}", 1, 0, 'R')
        pdf.cell(col_widths[3], 10, f"{item['amount']:,.2f}", 1, 0, 'R')
        pdf.ln()
    
    # Total
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(sum(col_widths[:-1]), 10, 'Total:', 1, 0, 'R')
    pdf.cell(col_widths[-1], 10, f"{quote_data['total']:,.2f}", 1, 0, 'R')
    
    return pdf

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    if len(hex_color) != 6:
        return (0, 0, 0)
    try:
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    except ValueError:
        return (0, 0, 0)

def company_settings():
    st.sidebar.header("Company Settings")
    ci = st.session_state.company_info
    
    ci['name'] = st.sidebar.text_input("Company Name", ci['name'])
    ci['address'] = st.sidebar.text_area("Address", ci['address'])
    ci['phone'] = st.sidebar.text_input("Phone", ci['phone'])
    ci['email'] = st.sidebar.text_input("Email", ci['email'])
    ci['footer_text'] = st.sidebar.text_area("Footer Text", ci['footer_text'])
    ci['theme_color'] = st.sidebar.color_picker("Theme Color", ci['theme_color'])
    
    new_logo = st.sidebar.file_uploader("Upload Logo", type=['png', 'jpg', 'jpeg'])
    if new_logo:
        ci['logo'] = new_logo

def main():
    st.set_page_config(page_title="Quotation Generator", layout="wide")
    initialize_session_state()
    
    # Sidebar settings
    company_settings()
    
    # Main tabs
    tab1, tab2 = st.tabs(["Create Quotation", "Quotation History"])
    
    with tab1:
        st.title("Create New Quotation")
        
        # Client Information
        st.subheader("Client Details")
        ci = st.session_state.client_info
        cols = st.columns(2)
        ci['name'] = cols[0].text_input("Name", ci['name'])
        ci['email'] = cols[1].text_input("Email", ci['email'])
        ci['phone'] = cols[0].text_input("Phone", ci['phone'])
        ci['address'] = cols[1].text_input("Address", ci['address'])

        # Item Management
        st.subheader("Items")
        with st.form("item_form"):
            cols = st.columns([3, 1, 1, 2])
            desc = cols[0].text_input("Description", key='description')
            unit_cost = cols[1].number_input("Unit Cost", min_value=0.0, key='unit_cost')
            quantity = cols[2].number_input("Quantity", min_value=0.0, step=0.1, key='quantity')
            
            cols = st.columns(2)
            submit_label = 'Update Item' if st.session_state.editing_index is not None else 'Add Item'
            cols[0].form_submit_button(submit_label, on_click=add_item)
            cols[1].form_submit_button("Clear All", on_click=clear_form)

        # Display Items
        if st.session_state.itemss:
            st.subheader("Current Items")
            df = pd.DataFrame(st.session_state.itemss)
            df['Amount'] = df['unit_cost'] * df['quantity']
            styled_df = df.style.format({
                'unit_cost': "KES {:,.2f}",
                'quantity': "{:,.2f}",
                'amount': "KES {:,.2f}"
            })
            
            st.dataframe(styled_df, use_container_width=True)
            
            # Action buttons for each item
            for idx in range(len(st.session_state.itemss)):
                cols = st.columns([5, 1, 1])
                cols[1].button("Edit", key=f"edit_{idx}", on_click=edit_item, args=(idx,))
                cols[2].button("Delete", key=f"del_{idx}", on_click=delete_item, args=(idx,))

            # Total and generation
            total = df['amount'].sum()
            st.markdown(f"**Total Amount: KES {total:,.2f}**")
            
            if st.button("Generate Quotation"):
                json_file, pdf_file = save_quotation()
                if json_file and pdf_file:
                    cols = st.columns(2)
                    with open(pdf_file, "rb") as f:
                        cols[0].download_button("Download PDF", f, file_name=pdf_file)
                    with open(json_file, "rb") as f:
                        cols[1].download_button("Download JSON", f, file_name=json_file)
                    clear_form()

    with tab2:
        st.title("Quotation History")
        search_term = st.text_input("Search by client name, quote number, or date")
        
        try:
            quotes = load_quotation_history()
            if search_term:
                quotes = [q for q in quotes if search_term.lower() in str(q.values()).lower()]
            
            if not quotes:
                st.info("No quotations found")
                return
                
            for quote in quotes:
                with st.expander(f"Quote #{quote['quote_number']} - {quote['client_info']['name']}"):
                    cols = st.columns([3, 1])
                    cols[0].write(f"**Date:** {quote['date']}")
                    cols[1].write(f"**Total:** KES {quote['total']:,.2f}")
                    
                    if st.button("Regenerate PDF", key=f"reg_{quote['quote_number']}"):
                        pdf = create_pdf(quote, quote['company_info'])  # Use original company info
                        pdf_file = f"quotation_{quote['quote_number']}.pdf"
                        pdf.output(pdf_file)
                        with open(pdf_file, "rb") as f:
                            st.download_button("Download PDF", f, file_name=pdf_file)
        except Exception as e:
            st.error(f"Error loading quotations: {str(e)}")

def load_quotation_history():
    quotes = []
    for json_file in glob.glob("quotation_*.json"):
        try:
            with open(json_file) as f:
                quotes.append(json.load(f))
        except Exception as e:
            st.error(f"Error loading {json_file}: {str(e)}")
    return sorted(quotes, key=lambda x: x['date'], reverse=True)

if __name__ == "__main__":
    main()