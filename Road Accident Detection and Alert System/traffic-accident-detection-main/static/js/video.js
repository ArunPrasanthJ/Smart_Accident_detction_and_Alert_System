document.addEventListener("DOMContentLoaded", function () {

  const notificationButton =
    document.getElementById("notificationButton");

  const notificationClose =
    document.getElementById("notificationClose");

  const notificationPanel =
    document.getElementById("notificationPanel");

  notificationButton.addEventListener(
    "click",
    function () {

      notificationPanel.classList.add("open");

      loadNotifications();

    }
  );

  notificationClose.addEventListener(
    "click",
    function () {

      notificationPanel.classList.remove("open");

    }
  );

  document.addEventListener(
    "keydown",
    function (event) {

      if (event.key === "Escape") {

        notificationPanel.classList.remove("open");

      }

    }
  );

  loadNotifications();

  setInterval(
    loadNotifications,
    3000
  );

});

async function loadNotifications() {

  try {

    const response = await fetch(
      document.body.dataset.notificationsUrl,
      {
        method: "GET",
        cache: "no-store"
      }
    );

    if (!response.ok) {

      throw new Error(
        "Notification request failed: " +
        response.status
      );

    }

    const data =
      await response.json();

    displayNotifications(
      data.notifications || []
    );

  }

  catch (error) {

    console.error(
      "Notification error:",
      error
    );

  }

}

function displayNotifications(notifications) {

  const list =
    document.getElementById(
      "notificationList"
    );

  const count =
    document.getElementById(
      "notificationCount"
    );

  if (
    !notifications ||
    notifications.length === 0
  ) {

    list.innerHTML = `

      <div class="no-notification">

        No notifications yet.

      </div>

    `;

    count.textContent = "0";

    return;

  }

  count.textContent =
    notifications.length;

  list.innerHTML = "";

  notifications.forEach(
    function (notification) {

      let icon = "🔔";

      if (
        notification.type === "email"
      ) {

        icon = "📧";

      }

      else if (
        notification.type === "database"
      ) {

        icon = "🗄️";

      }

      else if (
        notification.type === "accident"
      ) {

        icon = "⚠️";

      }

      else if (
        notification.type === "success"
      ) {

        icon = "✅";

      }

      const item =
        document.createElement(
          "div"
        );

      item.className =
        "notification-item " +
        (notification.type || "");

      const iconElement =
        document.createElement(
          "div"
        );

      iconElement.className =
        "notification-icon";

      iconElement.textContent =
        icon;

      const content =
        document.createElement(
          "div"
        );

      content.className =
        "notification-content";

      const title =
        document.createElement(
          "h4"
        );

      title.textContent =
        notification.title ||
        "Notification";

      const message =
        document.createElement(
          "p"
        );

      message.textContent =
        notification.message ||
        "";

      const time =
        document.createElement(
          "div"
        );

      time.className =
        "notification-time";

      time.textContent =
        notification.time ||
        "";

      content.appendChild(title);
      content.appendChild(message);
      content.appendChild(time);

      item.appendChild(iconElement);
      item.appendChild(content);

      list.appendChild(item);

    }
  );

}
