(function () {
    const STORAGE_KEY = 'discount_selected_products';
    const form = document.getElementById('discount-form');
    const selectAll = document.getElementById('select-all');
    const countEl = document.getElementById('selection-count');
    const clearBtn = document.getElementById('clear-selection');
    
    function getStored() {
      try {
        return new Set(JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]'));
      } catch (e) {
        return new Set();
      }
    }
    
    function setStored(set) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify([...set]));
      updateCount(set);
    }
    
      function updateCount(set) {
        countEl.textContent = `${set.size} selected`;
        document.getElementById('selection-bar').style.display = set.size > 0 ? 'flex' : 'none';
      }
    
    const stored = getStored();
    document.querySelectorAll('.row-check').forEach(cb => {
      if (stored.has(cb.value)) cb.checked = true;
    });
    updateCount(stored);
    
    
    document.querySelectorAll('.row-check').forEach(cb => {
      cb.addEventListener('change', function () {
        const set = getStored();
        if (this.checked) set.add(this.value);
        else set.delete(this.value);
        setStored(set);
      });
    });
    
    
    selectAll.addEventListener('change', function () {
      const set = getStored();
      document.querySelectorAll('.row-check').forEach(cb => {
        cb.checked = this.checked;
        if (this.checked) set.add(cb.value);
        else set.delete(cb.value);
      });
      setStored(set);
    });
    
    clearBtn.addEventListener('click', function () {
      localStorage.removeItem(STORAGE_KEY);
      document.querySelectorAll('.row-check').forEach(cb => cb.checked = false);
      updateCount(new Set());
    });
    
    
    form.addEventListener('submit', function () {
      const set = getStored();
      const onPageIds = new Set(
        [...document.querySelectorAll('.row-check')].map(cb => cb.value)
      );
      set.forEach(id => {
        if (!onPageIds.has(id)) {
          const hidden = document.createElement('input');
          hidden.type = 'hidden';
          hidden.name = 'product_ids';
          hidden.value = id;
          form.appendChild(hidden);
        }
      });
    });
    
    
    if (document.getElementById('discount-success-flag')) {
      localStorage.removeItem(STORAGE_KEY);
    }
    })();