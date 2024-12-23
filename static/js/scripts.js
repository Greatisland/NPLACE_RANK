document.addEventListener('DOMContentLoaded', () => {
    const toggleSidebar = () => {
        const sidebar = document.getElementById("sidebar");
        const overlay = document.getElementById("overlay");
        sidebar.classList.toggle("active");
        overlay.classList.toggle("active");
    };

    const closeSidebar = () => {
        const sidebar = document.getElementById("sidebar");
        const overlay = document.getElementById("overlay");
        sidebar.classList.remove("active");
        overlay.classList.remove("active");
    };

    const menuBtn = document.getElementById("menuBtn");
    const overlay = document.getElementById("overlay");
    const sidebar = document.getElementById("sidebar");

    if(menuBtn){
        menuBtn.addEventListener('click', toggleSidebar);
    }

    if(overlay){
        overlay.addEventListener('click', closeSidebar);
    }

    // 사이드바 외부 클릭 시 닫기
    document.addEventListener('click', (event) => {
        if (sidebar.classList.contains('active') &&
            !sidebar.contains(event.target) &&
            !menuBtn.contains(event.target)) {
            closeSidebar();
        }
    });

    // 스크롤 최상단 버튼
    const scrollToTopBtn = document.getElementById('scrollToTopBtn');
    const content = document.querySelector('.content'); // 스크롤을 체크할 요소

    if(scrollToTopBtn && content){
        content.addEventListener('scroll', () => {
            if (content.scrollTop > 300) {
                scrollToTopBtn.style.display = 'flex';
            } else {
                scrollToTopBtn.style.display = 'none';
            }
        });

        scrollToTopBtn.addEventListener('click', () => {
            content.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });
    }
});
