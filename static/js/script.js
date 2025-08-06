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
            condition: condition,
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
            const response = await fetch('/api/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    product_name: productName,
                    condition: condition, // Send simple condition values: 'all', 'new', 'used'
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

        // Debug: log the first product to see the data structure
        console.log('First product data:', products[0]);
        console.log('All products:', products);

        let tableHTML = `
            <table>
                <thead>
                    <tr>
                        <th>Product Title</th>
                        <th>Price</th>
                        <th>Condition</th>
                        <th>Seller Rating</th>
                        <th>Item Origin</th>
                        <th>View Product</th>
                    </tr>
                </thead>
                <tbody>
        `;

        products.forEach((product, index) => {
            const price = product["Price"];
            const currency = product["Currency"];
            const title = product["Product Title"];
            const condition = product["Condition"];
            const rating = product["Seller Rating (%)"];
            const feedbackCount = product["Seller Feedback Count"];
            const origin = product["Item Country"];
            const productUrl = product["Product URL"];

            // Debug: log condition for each product
            console.log(`Product ${index + 1} condition:`, condition, 'Type:', typeof condition);

            // Get appropriate class and display text for condition
            const { conditionClass, displayText } = getConditionInfo(condition);
            
            // Debug: log the result
            console.log(`Product ${index + 1} result:`, { conditionClass, displayText });

            tableHTML += `
                <tr>
                    <td class="product-title">${title}</td>
                    <td><span class="price">${price} ${currency}</span></td>
                    <td><span class="condition ${conditionClass}">${displayText}</span></td>
                    <td><span class="rating">${rating}% (${feedbackCount} feedback)</span></td>
                    <td><span class="origin ${origin ? 'origin-' + origin.toLowerCase() : ''}">${origin || 'N/A'}</span></td>
                    <td><a href="${productUrl}" target="_blank" class="view-btn">View</a></td>
                </tr>
            `;
        });

        tableHTML += `
                </tbody>
            </table>
        `;

        resultsContainer.innerHTML = tableHTML;
    }

    // Helper function for condition information
    function getConditionInfo(condition) {
        // Debug: log the actual condition value received
        console.log('getConditionInfo called with:', condition, 'Type:', typeof condition);
        
        // Handle null, undefined, or empty conditions
        if (!condition || condition === 'undefined' || condition === 'null') {
            console.log('Returning unknown for empty condition');
            return {
                conditionClass: 'condition-unknown',
                displayText: 'Unknown'
            };
        }
        
        // Convert to string and normalize
        const normalizedCondition = String(condition).toUpperCase().trim();
        console.log('Normalized condition:', normalizedCondition);
        
        const conditionMap = {
            // New conditions
            'NEW': {
                conditionClass: 'condition-new',
                displayText: 'New'
            },
            'LIKE_NEW': {
                conditionClass: 'condition-like-new',
                displayText: 'Like New'
            },
            'NEW_OTHER': {
                conditionClass: 'condition-new-other',
                displayText: 'New (Other)'
            },
            'NEW_WITH_DEFECTS': {
                conditionClass: 'condition-new-defects',
                displayText: 'New with Defects'
            },
            
            // Used conditions
            'PRE_OWNED_EXCELLENT': {
                conditionClass: 'condition-used-excellent',
                displayText: 'Pre-owned Excellent'
            },
            'USED_EXCELLENT': {
                conditionClass: 'condition-used-excellent',
                displayText: 'Used Excellent'
            },
            'USED_VERY_GOOD': {
                conditionClass: 'condition-used-very-good',
                displayText: 'Used Very Good'
            },
            'USED_GOOD': {
                conditionClass: 'condition-used-good',
                displayText: 'Used Good'
            },
            'USED_ACCEPTABLE': {
                conditionClass: 'condition-used-acceptable',
                displayText: 'Used Acceptable'
            },
            
            // Refurbished conditions
            'CERTIFIED_REFURBISHED': {
                conditionClass: 'condition-certified-refurb',
                displayText: 'Certified Refurbished'
            },
            'EXCELLENT_REFURBISHED': {
                conditionClass: 'condition-excellent-refurb',
                displayText: 'Excellent Refurbished'
            },
            'VERY_GOOD_REFURBISHED': {
                conditionClass: 'condition-very-good-refurb',
                displayText: 'Very Good Refurbished'
            },
            'GOOD_REFURBISHED': {
                conditionClass: 'condition-good-refurb',
                displayText: 'Good Refurbished'
            },
            'SELLER_REFURBISHED': {
                conditionClass: 'condition-seller-refurb',
                displayText: 'Seller Refurbished'
            },
            
            // Parts only
            'FOR_PARTS_OR_NOT_WORKING': {
                conditionClass: 'condition-parts',
                displayText: 'For Parts/Not Working'
            },
            
            // Legacy conditions (for backward compatibility)
            'USED': {
                conditionClass: 'condition-used',
                displayText: 'Used'
            },
            'VERY_GOOD': {
                conditionClass: 'condition-very-good',
                displayText: 'Very Good'
            },
            'GOOD': {
                conditionClass: 'condition-good',
                displayText: 'Good'
            },
            'ACCEPTABLE': {
                conditionClass: 'condition-acceptable',
                displayText: 'Acceptable'
            },
            'FAIR': {
                conditionClass: 'condition-fair',
                displayText: 'Fair'
            },
            
            // Unknown
            'UNKNOWN': {
                conditionClass: 'condition-unknown',
                displayText: 'Unknown'
            }
        };

        // Try exact match first
        if (conditionMap[normalizedCondition]) {
            console.log('Exact match found:', conditionMap[normalizedCondition]);
            return conditionMap[normalizedCondition];
        }
        
        // Try partial matches for common variations
        for (const [key, value] of Object.entries(conditionMap)) {
            if (normalizedCondition.includes(key) || key.includes(normalizedCondition)) {
                console.log('Partial match found:', value);
                return value;
            }
        }
        
        // Special handling for refurbished items
        if (normalizedCondition.includes('REFURBISHED')) {
            if (normalizedCondition.includes('EXCELLENT')) {
                console.log('Refurbished match - Excellent');
                return conditionMap['EXCELLENT_REFURBISHED'];
            } else if (normalizedCondition.includes('VERY_GOOD')) {
                console.log('Refurbished match - Very Good');
                return conditionMap['VERY_GOOD_REFURBISHED'];
            } else if (normalizedCondition.includes('GOOD')) {
                console.log('Refurbished match - Good');
                return conditionMap['GOOD_REFURBISHED'];
            } else if (normalizedCondition.includes('CERTIFIED')) {
                console.log('Refurbished match - Certified');
                return conditionMap['CERTIFIED_REFURBISHED'];
            } else if (normalizedCondition.includes('SELLER')) {
                console.log('Refurbished match - Seller');
                return conditionMap['SELLER_REFURBISHED'];
            } else {
                console.log('Generic refurbished match');
                return {
                    conditionClass: 'condition-seller-refurb',
                    displayText: 'Refurbished'
                };
            }
        }
        
        // Special handling for used items with quality indicators
        if (normalizedCondition.includes('USED') || normalizedCondition.includes('PRE_OWNED')) {
            if (normalizedCondition.includes('EXCELLENT')) {
                return conditionMap['USED_EXCELLENT'];
            } else if (normalizedCondition.includes('VERY_GOOD')) {
                return conditionMap['USED_VERY_GOOD'];
            } else if (normalizedCondition.includes('GOOD')) {
                return conditionMap['USED_GOOD'];
            } else if (normalizedCondition.includes('ACCEPTABLE')) {
                return conditionMap['USED_ACCEPTABLE'];
            } else {
                return conditionMap['USED'];
            }
        }
        
        // If no match found, return the original condition with unknown styling
        console.log('No match found, returning unknown');
        return {
            conditionClass: 'condition-unknown',
            displayText: condition || 'Unknown'
        };
    }
   
    // Display error message
    function displayError(message) {
        const friendlyMessages = {
            'Failed to fetch products': 'Service unavailable. Please try again later.',
            'NetworkError': 'Connection problem. Check your network and try again.'
        };
       
        resultsContainer.innerHTML = `
            <div class="error-message">
                <i class="fa-solid fa-triangle-exclamation"></i>
                <p>${friendlyMessages[message] || message}</p>
            </div>
        `;
        resultsHeader.classList.add('hidden');
    }
});