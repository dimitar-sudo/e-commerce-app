document.addEventListener('DOMContentLoaded', () => {
    const searchForm = document.getElementById('searchForm');
    const searchBtn = document.getElementById('searchBtn');
    const exportBtn = document.getElementById('exportBtn');
    const exportModal = document.getElementById('exportModal');
    const closeModal = document.getElementById('closeModal');
    const resultsContainer = document.getElementById('resultsContainer');
    const resultsHeader = document.getElementById('resultsHeader');
    const resultsCount = document.getElementById('resultsCount');
    
    let currentResults = [];
    let currentSearchParams = {};

    // Form submission handler
    searchForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // Get form values
        const productName = document.getElementById('productName').value;
        const condition = document.getElementById('condition').value;
        const currency = document.getElementById('currency').value;
        const sortBy = document.getElementById('sortBy').value;
        
        // Save current search params for export
        currentSearchParams = {
            product_name: productName,
            condition,
            currency,
            sort_by: sortBy
        };
        
        // Show loading state
        searchBtn.classList.add('loading');
        const spinner = searchBtn.querySelector('.spinner');
        const btnText = searchBtn.querySelector('.btn-text');
        spinner.classList.remove('hidden');
        btnText.textContent = 'Searching...';
        
        try {
            // Make API request
            const response = await fetch('/api/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    product_name: productName,
                    condition: condition,
                    currency: currency,
                    sort_by: sortBy
                })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Failed to fetch products');
            }
            
            // Save results for export
            currentResults = data.products;
            
            // Display results
            displayResults(data.products, data.count);
        } catch (error) {
            console.error('Search error:', error);
            displayError(error.message || 'An error occurred during search');
        } finally {
            // Reset button state
            spinner.classList.add('hidden');
            btnText.textContent = 'Search Products';
            searchBtn.classList.remove('loading');
        }
    });
    
    // Export button handler
    exportBtn.addEventListener('click', () => {
        if (currentResults.length === 0) {
            alert('No results to export. Please perform a search first.');
            return;
        }
        exportModal.classList.remove('hidden');
    });
    
    // Close modal handlers
    closeModal.addEventListener('click', () => {
        exportModal.classList.add('hidden');
    });
    
    window.addEventListener('click', (e) => {
        if (e.target === exportModal) {
            exportModal.classList.add('hidden');
        }
    });
    
    // Export option handlers
    document.querySelectorAll('.export-option').forEach(option => {
        option.addEventListener('click', () => {
            const format = option.dataset.format;
            window.location.href = `/api/export?format=${format}`;
            exportModal.classList.add('hidden');
        });
    });
    
    // Display search results
    function displayResults(products, count) {
        resultsHeader.classList.remove('hidden');
        resultsCount.textContent = `${count} ${count === 1 ? 'result' : 'results'} found`;
        
        if (products.length === 0) {
            resultsContainer.innerHTML = `
                <div class="placeholder">
                    <i class="fa-solid fa-face-frown"></i>
                    <p>No products found. Try a different search term.</p>
                </div>
            `;
            return;
        }
        
        let tableHTML = `
            <table>
                <thead>
                    <tr>
                        <th>Product</th>
                        <th>Price</th>
                        <th>Condition</th>
                        <th>Seller Rating</th>
                    </tr>
                </thead>
                <tbody>
        `;
        
        products.forEach(product => {
            const conditionClass = product.condition?.toLowerCase() === 'new' ? 
                'condition-new' : 'condition-used';
            
            tableHTML += `
                <tr>
                    <td class="product-name">${product.title}</td>
                    <td class="price">${product.converted_price}</td>
                    <td><span class="condition ${conditionClass}">${product.condition}</span></td>
                    <td><span class="rating">${'★'.repeat(Math.round(product.seller_rating || 0))}</span></td>
                </tr>
            `;
        });
        
        tableHTML += `
                </tbody>
            </table>
        `;
        
        resultsContainer.innerHTML = tableHTML;
    }
    
    // Display error message
    function displayError(message) {
        resultsContainer.innerHTML = `
            <div class="error-message">
                <i class="fa-solid fa-triangle-exclamation"></i>
                <p>${message}</p>
            </div>
        `;
        resultsHeader.classList.add('hidden');
    }
});