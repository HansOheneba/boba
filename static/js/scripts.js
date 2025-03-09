// document.addEventListener("alpine:init", () => {
//   Alpine.data("appState", () => ({
//     showModal: false,
//     showToppingsModal: false,
//     showShawarmaModal: false,
//     showIceTeaModal: false,
//     total: 0,
//     orderNumber: "",
//     name: localStorage.getItem("name") || "",
//     location: localStorage.getItem("location") || "",
//     preferences: "",
//     phone: localStorage.getItem("phone") || "",
//     email: localStorage.getItem("email") || "",
//     selectedBoba: "",
//     selectedShawarma: "",
//     selectedShawarmaType: "",
//     selectedBobaType: "",
//     selectedIceTeaType: "",
//     isLoading: true,
//     selectedBobaSize: "Large",
//     selectedBobaTopping: "No Toppings",
//     disableToppings: false,
//     selectedBobaQuantity: 1,
//     selectedShawarmaQuantity: 1,
//     selectedIceTeaQuantity: 1,
//     selectedIceTeaSize: "Medium",
//     cart: [],
//     paymentMethod: "paid", // Default payment method

//     init() {
//       window.addEventListener("load", () => {
//         this.isLoading = false;
//         this.updatePaymentMethod(this.paymentMethod); // Set default payment method on load
//       });
//     },

//     selectBobaType(type) {
//       this.selectedBobaType = type;
//       this.selectedBobaSize = "Large";
//       this.selectedBobaTopping = "No Toppings";
//       this.selectedBobaQuantity = 1;
//       this.disableToppings = false;
//       this.showToppingsModal = true;
//     },

//     addToppings() {
//       const size = this.selectedBobaSize;
//       const topping = this.selectedBobaTopping;
//       const quantity = this.selectedBobaQuantity;
//       const selectedBobaType = this.selectedBobaType;
//       let price = size === "Large" ? 40 : 30;

//       if (size === "Medium") {
//         price = 30;
//         this.addToCart(selectedBobaType + " (" + size + ")", price, quantity);
//       } else {
//         this.addToCart(
//           selectedBobaType + " (" + size + ") with " + topping,
//           price,
//           quantity
//         );
//       }

//       this.showToppingsModal = false;
//     },

//     selectShawarmaType(type) {
//       this.selectedShawarmaType = type;
//       this.selectedShawarmaQuantity = 1;
//       this.showShawarmaModal = true;
//     },

//     addShawarma() {
//       const size = document.querySelector(
//         'input[name="shawarma_size"]:checked'
//       ).value;
//       const quantity = this.selectedShawarmaQuantity;
//       const selectedShawarmaType = this.selectedShawarmaType;
//       let price =
//         size === "Medium"
//           ? selectedShawarmaType.includes("Chicken")
//             ? 35
//             : 40
//           : selectedShawarmaType.includes("Chicken")
//           ? 45
//           : 50;

//       this.addToCart(selectedShawarmaType + " (" + size + ")", price, quantity);
//       this.showShawarmaModal = false;
//     },

//     selectIceTeaType(type) {
//       this.selectedIceTeaType = type;
//       this.selectedIceTeaSize = "Medium";
//       this.selectedIceTeaQuantity = 1;
//       this.showIceTeaModal = true;
//     },

//     addIceTea() {
//       const size = this.selectedIceTeaSize;
//       const quantity = this.selectedIceTeaQuantity;
//       const selectedIceTeaType = this.selectedIceTeaType;
//       let price = size === "Large" ? 40 : 30;

//       this.addToCart(selectedIceTeaType + " (" + size + ")", price, quantity);
//       this.showIceTeaModal = false;
//     },

//     addToCart(item, price, quantity = 1) {
//       let existingItem = this.cart.find((cartItem) => cartItem.name === item);
//       if (existingItem) {
//         existingItem.quantity += quantity;
//       } else {
//         this.cart.push({ name: item, price: price, quantity: quantity });
//       }
//       this.updateCart();
//     },

//     removeFromCart(index) {
//       if (this.cart[index].quantity > 1) {
//         this.cart[index].quantity -= 1;
//       } else {
//         this.cart.splice(index, 1);
//       }
//       this.updateCart();
//     },

//     updateCart() {
//       let cartList = document.getElementById("cart");
//       cartList.innerHTML = "";
//       let total = 0;
//       this.cart.forEach((item, index) => {
//         let li = document.createElement("li");
//         li.innerHTML = `${
//           item.name
//         } <span style="font-weight: bold; color: #ff9fe5;">x${
//           item.quantity
//         }</span> - <span style="font-weight: bold; color: #ff9fe5;">${
//           item.price * item.quantity
//         } GHS</span>`;
//         li.classList.add("cursor-pointer", "hover:text-red-500");
//         li.onclick = () => this.removeFromCart(index);
//         let removeButton = document.createElement("span");
//         removeButton.textContent = " x";
//         removeButton.classList.add("text-red-500", "cursor-pointer", "ml-2");
//         removeButton.onclick = () => this.removeFromCart(index);
//         li.appendChild(removeButton);
//         cartList.appendChild(li);
//         total += item.price * item.quantity;
//       });
//       document.getElementById("total").textContent = total;
//       document.getElementById("total-input").value = total;
//       document.getElementById("order-input").value = this.cart
//         .map((item) => `${item.name} x${item.quantity}`)
//         .join(", ");

//       if (total > 0) {
//         document.getElementById("total-container").classList.remove("hidden");
//       } else {
//         document.getElementById("total-container").classList.add("hidden");
//       }

//       document.getElementById("order-summary").textContent = this.cart
//         .map((item) => `${item.name} x${item.quantity}`)
//         .join(", ");
//     },

//     generateOrderNumber() {
//       const chars = "abcdefghijklmnopqrstuvwxyz0123456789";
//       let result = "boba-";
//       for (let i = 0; i < 4; i++) {
//         result += chars.charAt(Math.floor(Math.random() * chars.length));
//       }
//       return result;
//     },

//     validateForm() {
//       const form = document.getElementById("order-form");
//       if (form.checkValidity() && this.cart.length > 0) {
//         this.showModal = true;
//         this.total = document.getElementById("total").textContent;
//         this.orderNumber = this.generateOrderNumber();
//       } else {
//         form.reportValidity();
//         if (this.cart.length === 0) {
//           alert("Please select at least one item.");
//         }
//       }
//     },

//     updatePaymentMethod(method) {
//       this.paymentMethod = method;
//       document.getElementById("payment_method").value = method;
//     },

//     handleOrderConfirmation() {
//       if (this.paymentMethod === "paid") {
//         this.payWithPaystack();
//       } else {
//         document.querySelector("#order-form").submit();
//       }
//     },

//     payWithPaystack() {
//       const handler = PaystackPop.setup({
//         key: "pk_test_ab9e41a1a26c75b8f9834facfc309cb860ae3330", // Replace with your Paystack public key
//         email: this.email,
//         amount: this.total * 100, // Amount in kobo
//         currency: "GHS",
//         ref: this.orderNumber,
//         callback: function (response) {
//           document.querySelector("form").submit();
//         },
//         onClose: function () {
//           alert("Payment cancelled");
//         },
//       });
//       handler.openIframe();
//     },
//   }));
// });

// document.addEventListener("DOMContentLoaded", function () {
//   const storedName = localStorage.getItem("name");
//   const storedLocation = localStorage.getItem("location");
//   const storedPhone = localStorage.getItem("phone");
//   const storedEmail = localStorage.getItem("email");

//   if (storedName) document.querySelector("[name='name']").value = storedName;
//   if (storedLocation)
//     document.querySelector("[name='location']").value = storedLocation;
//   if (storedPhone) document.querySelector("[name='phone']").value = storedPhone;
//   if (storedEmail) document.querySelector("[name='email']").value = storedEmail;

//   document
//     .querySelector("[name='name']")
//     .addEventListener("input", function () {
//       localStorage.setItem("name", this.value);
//     });
//   document
//     .querySelector("[name='location']")
//     .addEventListener("input", function () {
//       localStorage.setItem("location", this.value);
//     });
//   document
//     .querySelector("[name='phone']")
//     .addEventListener("input", function () {
//       localStorage.setItem("phone", this.value);
//     });
//   document
//     .querySelector("[name='email']")
//     .addEventListener("input", function () {
//       localStorage.setItem("email", this.value);
//     });
// });
