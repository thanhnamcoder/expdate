
// Thêm hàm showLoading và hideLoading
function showLoading(container) {
    if (!container) return;
    
    container.innerHTML = `
        <div class="text-center py-5">
            <div class="spinner-border text-primary" role="status" style="width: 3rem; height: 3rem;">
                <span class="visually-hidden">Đang tải...</span>
            </div>
            <div class="mt-3 text-muted">
                <strong>Đang tải dữ liệu...</strong>
            </div>
        </div>
    `;
}

function hideLoading(container) {
    // Loading sẽ được thay thế bằng nội dung thực tế
    // Hàm này có thể để trống hoặc thêm animation fade out nếu cần
}

function showAlertMessage(message, type = "info", timeout = 2000) {
    const alertBox = document.getElementById("scan-alert");

    if (!alertBox) {
        console.error("Không tìm thấy phần tử 'scan-alert' trong DOM.");
        return;
    }

    alertBox.className = `alert alert-${type} alert-dismissible fade show text-center mb-0 rounded-0`;
    alertBox.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;

    if (timeout > 0) {
        setTimeout(() => {
            alertBox.classList.remove("show");
            alertBox.classList.add("d-none");
        }, timeout);
    }
}



function showTab(tabId, clickedElement) {
    document.querySelectorAll('.tab-pane').forEach(tab => tab.classList.remove('show', 'active'));
    document.getElementById(tabId).classList.add('show', 'active');
    document.querySelectorAll('.bottom-nav .nav-link').forEach(link => link.classList.remove('active'));
    clickedElement.classList.add('active');
    
    // THÊM DÒNG NÀY
    if (tabId === 'dataTab') {
        renderDataTab();
    }
}

let html5QrcodeScanner = null;
const html5QrCodeId = "html5qr-reader";
const scanStatus = document.getElementById('scanStatus');

function openBarcodeScanner() {
    const modal = new bootstrap.Modal(document.getElementById('barcodeModal'));
    modal.show();

    if (!html5QrcodeScanner) {
        html5QrcodeScanner = new Html5Qrcode(html5QrCodeId);
    }

    startScanner();
}

function startScanner() {
    scanStatus.textContent = 'Đang chờ quét...';

    const config = {
        fps: 10,
        qrbox: 250,
        formatsToSupport: [
            Html5QrcodeSupportedFormats.CODE_128,
            Html5QrcodeSupportedFormats.CODE_39,
            Html5QrcodeSupportedFormats.EAN_13,
            Html5QrcodeSupportedFormats.EAN_8,
            Html5QrcodeSupportedFormats.UPC_A,
            Html5QrcodeSupportedFormats.UPC_E,
            Html5QrcodeSupportedFormats.QR_CODE,
            Html5QrcodeSupportedFormats.ITF,
            Html5QrcodeSupportedFormats.CODABAR,
            Html5QrcodeSupportedFormats.DATA_MATRIX,
            Html5QrcodeSupportedFormats.PDF_417,
        ]
    };

    html5QrcodeScanner.start(
        { facingMode: "environment" },
        config,
        qrCodeMessage => {
            document.getElementById('itembarcode').value = qrCodeMessage;

            fetch(`/api/get-item/?barcode=${qrCodeMessage}`, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json'
                }
            })
                .then(response => {
                    if (response.ok) {
                        return response.json();
                    } else {
                        throw new Error('Lỗi khi gọi API');
                    }
                })
                .then(data => {
                    if (data.success && data.data) {
                        document.getElementById('itemname').value = data.data.item_name;
                        updateNotificationMessage("Scan thành công!", "success");
                    } else {
                        console.warn('Không tìm thấy sản phẩm:', data.error || 'Không rõ lỗi');
                        document.getElementById('itemname').value = '';
                        updateNotificationMessage("Không tìm thấy sản phẩm!", "warning");
                    }
                })
                .catch(error => {
                    console.error('Lỗi khi gọi API:', error);
                    document.getElementById('itemname').value = '';
                    updateNotificationMessage("Lỗi khi gọi API!", "danger");
                });

            html5QrcodeScanner.stop()
                .then(() => {
                    const modalEl = document.getElementById('barcodeModal');
                    const modalInstance = bootstrap.Modal.getInstance(modalEl);
                    modalInstance.hide();
                })
                .catch(err => {
                    console.error('Lỗi khi dừng scanner:', err);
                });
        },
        errorMessage => {
            console.warn('Lỗi quét mã vạch:', errorMessage);
            updateNotificationMessage("Lỗi quét mã vạch!", "danger");
        }
    ).catch(err => {
        scanStatus.textContent = 'Không thể mở camera: ' + err;
        console.error('Lỗi khi khởi tạo scanner:', err);
        updateNotificationMessage("Không thể mở camera!", "danger");
    });
}

document.getElementById('barcodeModal').addEventListener('hidden.bs.modal', () => {
    if (html5QrcodeScanner) {
        html5QrcodeScanner.stop()
            .then(() => html5QrcodeScanner.clear())
            .catch(err => {
            });
    }
});

document.getElementById('itembarcode').addEventListener('input', async function () {
    const barcode = this.value.trim();
    if (barcode) {
        try {
            const response = await fetch(`/api/get-item/?barcode=${barcode}`, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json'
                }
            });
            if (response.ok) {
                const data = await response.json();
                if (data.success && data.data) {
                    document.getElementById('itemname').value = data.data.item_name;
                } else {
                    document.getElementById('itemname').value = '';
                }
            } else {
                document.getElementById('itemname').value = '';
            }
        } catch (error) {
            console.error('Lỗi kết nối:', error);
            document.getElementById('itemname').value = '';
        }
    } else {
        document.getElementById('itemname').value = '';
    }
});

document.querySelector('form').addEventListener('submit', async function (event) {
    event.preventDefault();

    const itembarcode = document.getElementById('itembarcode').value.trim();
    const itemname = document.getElementById('itemname').value.trim();
    const quantity = document.getElementById('quantity').value.trim();
    const expdate = document.getElementById('hsd').value.trim();

    const expdateRegex = /^\d{2}\/\d{2}\/\d{4}$/;
    if (!expdateRegex.test(expdate)) {
        updateNotificationMessage("Ngày hết hạn không hợp lệ!", "warning");
        return;
    }

    if (!itembarcode) {
        updateNotificationMessage("Vui lòng nhập mã barcode!", "warning");
        return;
    }
    if (!itemname) {
        updateNotificationMessage("Vui lòng nhập tên sản phẩm!", "warning");
        return;
    }
    if (!quantity) {
        updateNotificationMessage("Vui lòng nhập số lượng!", "warning");
        return;
    }
    if (!expdate) {
        updateNotificationMessage("Vui lòng nhập ngày hết hạn!", "warning");
        return;
    }

    try {
        const response = await fetch('/api/items/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({
                itembarcode,
                itemname,
                quantity,
                expdate
            })
        });

        if (response.ok) {
            const data = await response.json();
            if (data.created) {
                updateNotificationMessage("Thêm sản phẩm thành công!", "success");
            } else if (data.updated) {
                updateNotificationMessage("Lưu sản phẩm thành công!", "info");
            }

            // Clear form fields after successful save
            document.getElementById('itembarcode').value = '';
            document.getElementById('itemname').value = '';
            document.getElementById('quantity').value = '';
            document.getElementById('hsd').value = '';
            document.getElementById('monthsToAdd').value = '';
            document.getElementById('day').value = '1'; // Reset day to default value
            document.getElementById('month').value = '1'; // Reset month to default value
            document.getElementById('year').value = new Date().getFullYear().toString(); // Reset year to current year
            document.getElementById('addType').value = 'month'; // Reset addType to default value
        } else {
            const errorData = await response.json();
            updateNotificationMessage(`Lỗi: ${errorData.message || 'Không rõ lỗi'}`, "danger");
        }
    } catch (error) {
        console.error('Lỗi kết nối:', error);
        updateNotificationMessage("Lỗi kết nối đến máy chủ!", "danger");
    }
});

function calculateHSD() {
    const day = parseInt(document.getElementById('day').value);
    const month = parseInt(document.getElementById('month').value);
    const year = parseInt(document.getElementById('year').value);
    const monthsToAdd = parseInt(document.getElementById('monthsToAdd').value);
    const addType = document.getElementById('addType').value;

    const currentDate = new Date(year, month - 1, day);

    if (addType === 'month') {
        currentDate.setMonth(currentDate.getMonth() + monthsToAdd);
    } else if (addType === 'day') {
        currentDate.setDate(currentDate.getDate() + monthsToAdd);
    }

    const calculatedDay = currentDate.getDate().toString().padStart(2, '0');
    const calculatedMonth = (currentDate.getMonth() + 1).toString().padStart(2, '0');
    const calculatedYear = currentDate.getFullYear();

    const hsd = `${calculatedDay}/${calculatedMonth}/${calculatedYear}`;
    document.getElementById('hsd').value = hsd;
}

document.getElementById('monthsToAdd').addEventListener('input', calculateHSD);
document.getElementById('addType').addEventListener('change', calculateHSD);

document.getElementById('day').addEventListener('change', autoCalculateHSD);
document.getElementById('month').addEventListener('change', autoCalculateHSD);
document.getElementById('year').addEventListener('change', autoCalculateHSD);
document.getElementById('monthsToAdd').addEventListener('input', autoCalculateHSD);

function autoCalculateHSD() {
    const day = parseInt(document.getElementById('day').value);
    const month = parseInt(document.getElementById('month').value);
    const year = parseInt(document.getElementById('year').value);
    const monthsToAdd = parseInt(document.getElementById('monthsToAdd').value);
    const addType = document.getElementById('addType').value;

    if (!day || !month || !year || !monthsToAdd) {
        document.getElementById('hsd').value = '';
        return;
    }

    const currentDate = new Date(year, month - 1, day);

    if (addType === 'month') {
        currentDate.setMonth(currentDate.getMonth() + monthsToAdd);
    } else if (addType === 'day') {
        currentDate.setDate(currentDate.getDate() + monthsToAdd);
    }

    const calculatedDay = currentDate.getDate().toString().padStart(2, '0');
    const calculatedMonth = (currentDate.getMonth() + 1).toString().padStart(2, '0');
    const calculatedYear = currentDate.getFullYear();

    const hsd = `${calculatedDay}/${calculatedMonth}/${calculatedYear}`;
    document.getElementById('hsd').value = hsd;
}


document.getElementById('addType').addEventListener('change', function () {
    const monthsToAddLabel = document.querySelector("label[for='monthsToAdd']");
    if (this.value === 'day') {
        monthsToAddLabel.textContent = 'Số ngày';
        document.getElementById('monthsToAdd').placeholder = 'Nhập số ngày';
    } else {
        monthsToAddLabel.textContent = 'Số tháng';
        document.getElementById('monthsToAdd').placeholder = 'Nhập số tháng';
    }
});

function updateNotificationMessage(message, type = "info", timeout = 2000) {
    const notificationBox = document.getElementById("notification-box");
    const notificationMessage = document.getElementById("notification-message");

    if (!notificationBox || !notificationMessage) {
        console.error("Không tìm thấy phần tử 'notification-box' hoặc 'notification-message' trong DOM.");
        return;
    }

    const defaultMessage = "Thông báo sẽ hiển thị ở đây.";

    // Cập nhật nội dung và kiểu thông báo
    notificationBox.className = `alert alert-${type} d-flex align-items-center`;
    notificationMessage.textContent = message;

    // Luôn hiển thị thông báo
    notificationBox.classList.remove("d-none");

    // Sau timeout, quay lại nội dung mặc định
    setTimeout(() => {
        notificationMessage.textContent = defaultMessage;
        notificationBox.className = `alert alert-info d-flex align-items-center`;
    }, timeout);
}

// Hiển thị thông báo mặc định khi ứng dụng khởi động
document.addEventListener("DOMContentLoaded", () => {
    const notificationBox = document.getElementById("notification-box");
    if (notificationBox) {
        notificationBox.classList.remove("d-none");
    }
});

document.addEventListener("DOMContentLoaded", () => {
    renderDataTab(); // Gọi hàm khi DOM đã sẵn sàng
});


async function loadItemDetails() {
    try {
        const response = await fetch('/api/group-items/', {
            method: 'GET',
            headers: {
                'Accept': 'application/json'
            }
        });
        if (response.ok) {
            const data = await response.json();
            return data.items || [];
        } else {
            return [];
        }
    } catch (error) {
        return [];
    }
}

async function renderDataTab() {
    const items = await loadItemDetails();
    const container = document.getElementById('data-container');
    container.innerHTML = '';
    if (Array.isArray(items) && items.length > 0) {
        // Gom nhóm theo user
        const userMap = {};
        items.forEach(item => {
            const username = item.username || 'Không rõ';
            if (!userMap[username]) userMap[username] = [];
            userMap[username].push(item);
        });
        // Hiển thị danh sách user
        Object.keys(userMap).forEach(username => {
            const userBtn = document.createElement('button');
            userBtn.className = 'btn btn-outline-primary mb-2 me-2 user-data-btn';
            userBtn.textContent = username;
            userBtn.onclick = () => {
                showUserDataModal(username, userMap[username]);
            };
            container.appendChild(userBtn);
        });
    } else {
        container.innerHTML = '<div class="text-center text-muted">Không có dữ liệu.</div>';
    }
}

// Modal hiển thị dữ liệu user với nút sửa/xóa
let bsModalInstance = null; // Biến global để giữ instance modal

function createModal() {
  let modal = document.getElementById('userDataModal');
  if (!modal) {
    modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.id = 'userDataModal';
    modal.tabIndex = -1;
    modal.innerHTML = `
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header sticky-top bg-white" style="z-index:1056;">
            <h5 class="modal-title">Dữ liệu của <span id="modal-username"></span></h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="modal-body" style="max-height:70vh;overflow-y:auto;">
            <div class="row" id="modal-user-data-list"></div>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(modal);
    bsModalInstance = new bootstrap.Modal(modal);
  }
  return modal;
}

// Hàm render item bình thường (chưa edit)
function renderItemView(item, username, items) {
  const card = document.createElement('div');
  card.className = 'col-12 col-md-6 col-lg-4 mb-3';
  card.innerHTML = `
    <div class="card h-100 shadow-sm">
      <div class="card-body">
        <h5 class="card-title text-primary">${item.itemname || ''}</h5>
        <p class="mb-1"><strong>Barcode:</strong> ${item.itembarcode || ''}</p>
        <p class="mb-1"><strong>Số lượng:</strong> ${item.quantity || ''}</p>
        <p class="mb-1"><strong>HSD:</strong> ${item.expdate || ''}</p>
        ${item.can_edit ? `<button class="btn btn-primary btn-sm me-2" id="edit-btn-${item.itembarcode}">Sửa</button>` : ''}
        ${item.can_delete ? `<button class="btn btn-danger btn-sm" id="delete-btn-${item.itembarcode}">Xóa</button>` : ''}
      </div>
    </div>
  `;

  if (item.can_edit) {
    card.querySelector(`#edit-btn-${item.itembarcode}`).onclick = () => {
      item.isEditing = true;
      showUserDataModal(username, items);
    };
  }
  if (item.can_delete) {
    card.querySelector(`#delete-btn-${item.itembarcode}`).onclick = () => {
      handleDelete(item, items, username);
    };
  }
  return card;
}

// Hàm render item ở chế độ edit
function renderItemEdit(item, username, items) {
  const card = document.createElement('div');
  card.className = 'col-12 col-md-6 col-lg-4 mb-3';
  card.innerHTML = `
    <div class="card h-100 shadow-sm p-3 border border-primary">
      <div>
        <input class="form-control mb-2" type="text" value="${item.itemname || ''}" id="edit-name-${item.itembarcode}">
        <input class="form-control mb-2" type="text" value="${item.itembarcode || ''}" id="edit-barcode-${item.itembarcode}">
        <input class="form-control mb-2" type="number" value="${item.quantity || 0}" id="edit-qty-${item.itembarcode}">
        <input class="form-control mb-2" type="date" value="${item.expdate || ''}" id="edit-expdate-${item.itembarcode}">
        <button class="btn btn-success btn-sm me-2" id="save-btn-${item.itembarcode}">Lưu</button>
        <button class="btn btn-secondary btn-sm" id="cancel-btn-${item.itembarcode}">Hủy</button>
      </div>
    </div>
  `;

  card.querySelector(`#save-btn-${item.itembarcode}`).onclick = () => {
    const newName = card.querySelector(`#edit-name-${item.itembarcode}`).value.trim();
    const newBarcode = card.querySelector(`#edit-barcode-${item.itembarcode}`).value.trim();
    const newQty = parseInt(card.querySelector(`#edit-qty-${item.itembarcode}`).value);
    const newExpDate = card.querySelector(`#edit-expdate-${item.itembarcode}`).value;

    if (!newName) {
      alert('Tên không được để trống');
      return;
    }

    item.itemname = newName;
    item.itembarcode = newBarcode;
    item.quantity = newQty;
    item.expdate = newExpDate;
    item.isEditing = false;
    showUserDataModal(username, items);
  };

  card.querySelector(`#cancel-btn-${item.itembarcode}`).onclick = () => {
    item.isEditing = false;
    showUserDataModal(username, items);
  };

  return card;
}

// Hàm hiển thị modal dữ liệu user
function showUserDataModal(username, items) {
  let modal = document.getElementById('userDataModal');
  if (!modal) {
    modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.id = 'userDataModal';
    modal.tabIndex = -1;
    modal.innerHTML = `
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header sticky-top bg-white" style="z-index:1056;">
            <h5 class="modal-title">Dữ liệu của <span id="modal-username"></span></h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="modal-body" style="max-height:70vh;overflow-y:auto;">
            <div class="row" id="modal-user-data-list"></div>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(modal);
  }

  modal.querySelector('#modal-username').textContent = username;

  const dataList = modal.querySelector('#modal-user-data-list');
  dataList.innerHTML = '';

  items.forEach(item => {
    if (item.isEditing) {
      dataList.appendChild(renderItemEdit(item, username, items));
    } else {
      dataList.appendChild(renderItemView(item, username, items));
    }
  });

  const bsModal = bootstrap.Modal.getInstance(modal) || new bootstrap.Modal(modal);
  bsModal.show();
}





// Hàm xử lý xóa
function handleDelete(item, items, username) {
    if (confirm(`Bạn có chắc muốn xóa item: ${item.itemname}?`)) {
        const index = items.indexOf(item);
        if (index > -1) {
            items.splice(index, 1);
            showUserDataModal(username, items);
        }
    }
}

