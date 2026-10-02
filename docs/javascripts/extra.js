document.addEventListener("DOMContentLoaded", function() {
    const STORAGE_KEY = 'mkdocs_tasks_v2'; // New key for the unified structure
    
    // Auto-migrate from old bookmarks if needed
    try {
        const oldBms = JSON.parse(localStorage.getItem('mkdocs_bookmarks') || '[]');
        if (oldBms.length > 0 && !localStorage.getItem(STORAGE_KEY)) {
            let newTasks = {};
            oldBms.forEach(b => {
                newTasks[b.url] = {
                    id: b.url,
                    isBookmarked: true,
                    isCompleted: b.isCompleted || false,
                    codeExample: b.codeExample || '',
                    contentHtml: b.contentHtml || '',
                    title: b.title || 'Задача',
                    originalCategory: b.url.split('#')[0]
                };
            });
            localStorage.setItem(STORAGE_KEY, JSON.stringify(newTasks));
        }
    } catch(e) {}

    // Categories for the dropdown
    const CATEGORIES = [
        { id: '/livecoding/python/', name: 'Лайфкодинг / Python' },
        { id: '/livecoding/go/', name: 'Лайфкодинг / Go' },
        { id: '/livecoding/java/', name: 'Лайфкодинг / Java' },
        { id: '/livecoding/react/', name: 'Лайфкодинг / React' },
        { id: '/anatomy/python/', name: 'Анатомия языка / Python' },
        { id: '/anatomy/go/', name: 'Анатомия языка / Go' },
        { id: '/architecture/', name: 'Архитектура' },
        { id: '/databases/', name: 'Базы данных' },
        { id: '/management/', name: 'Менеджмент' }
    ];

    const AVAILABLE_TAGS = ['алгоритмы', 'основы языка', 'web', 'субд', 'индексы', 'асинхрон', 'dataflow'];

    function getTasks() { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}'); }
    function saveTasks(tasks) { localStorage.setItem(STORAGE_KEY, JSON.stringify(tasks)); }
    function getTask(id) { return getTasks()[id] || { id, linkedScripts: [] }; }
    function saveTask(task) { let t = getTasks(); t[task.id] = task; saveTasks(t); }

    let currentPath = window.location.pathname;
    if (currentPath.endsWith('index.html')) currentPath = currentPath.replace('index.html', '');
    
    // Process static <h2> tasks
    const h2s = Array.from(document.querySelectorAll('.md-content h2'));
    h2s.forEach(h2 => {
        if (!h2.textContent.trim().startsWith('Задача')) return;
        
        const taskId = currentPath + '#' + h2.id;
        const task = getTask(taskId);
        
        task.title = task.title || h2.textContent.replace('¶', '').trim();
        task.originalCategory = task.originalCategory || currentPath;
        
        h2.classList.add('task-title');
        
        let node = h2.nextElementSibling;
        let currentDetails = null;
        let currentContent = null;
        
        while(node && node.tagName !== 'H2') {
            const nextNode = node.nextElementSibling;
            
            if (node.tagName === 'H3' && (node.textContent.includes('Решение кандидата') || node.textContent.includes('Эталонное решение'))) {
                // If this is a static task that was already wrapped previously, don't re-wrap it?
                // Wait, MkDocs renders H3 natively, so it's only an H3 on fresh page load.
                currentDetails = document.createElement('details');
                currentDetails.className = 'script-details task-solution-details';
                
                const summary = document.createElement('summary');
                summary.textContent = node.textContent.replace('¶', '').trim();
                currentDetails.appendChild(summary);
                
                currentContent = document.createElement('div');
                currentContent.className = 'script-pre';
                currentContent.style.padding = '15px';
                currentContent.style.whiteSpace = 'normal'; // Allow text wrapping
                currentDetails.appendChild(currentContent);
                
                node.parentNode.insertBefore(currentDetails, node);
                node.parentNode.removeChild(node);
            } else if (node.tagName === 'H3') {
                currentDetails = null;
                currentContent = null;
            } else if (currentContent) {
                currentContent.appendChild(node);
            }
            
            node = nextNode;
        }

        let html = '';
        node = h2.nextElementSibling;
        while(node && node.tagName !== 'H2') {
            html += node.outerHTML;
            node = node.nextElementSibling;
        }
        task.contentHtml = html;
        
        task.linkedScripts = task.linkedScripts || [];
        
        // Auto-link dummy script to Task 16 for the first time
        if (task.title.includes('Задача 16:') && task.linkedScripts.length === 0 && !task._autoLinked) {
            task.linkedScripts.push({path: '/python_code/dummy_thread_pool.py', type: 'alternative'});
            task._autoLinked = true;
        }
        
        saveTask(task);
        
        // Hide if overridden
        if (task.customCategory && task.customCategory !== currentPath) {
            h2.style.display = 'none';
            let node = h2.nextElementSibling;
            while(node && node.tagName !== 'H2') {
                node.style.display = 'none';
                node = node.nextElementSibling;
            }
            
            // Hide from TOC
            const tocLink = document.querySelector(`.md-sidebar--primary a[href="#${h2.id}"]`);
            if (tocLink && tocLink.parentElement) {
                tocLink.parentElement.style.display = 'none';
            }
            
            return;
        }
        
        augmentTaskUI(h2, task);
    });
    
    // Fetch and render tasks moved TO this page
    const allTasks = getTasks();
    const tasksMovedHere = Object.values(allTasks).filter(t => t.customCategory === currentPath && t.originalCategory !== currentPath);
    if (tasksMovedHere.length > 0) {
        let container = document.querySelector('.md-typeset');
        if (!container) container = document.querySelector('.md-content__inner') || document.querySelector('.md-content');
        
        tasksMovedHere.forEach(task => {
            const h2 = document.createElement('h2');
            h2.id = task.id.split('#')[1];
            h2.textContent = task.title;
            h2.classList.add('task-title');
            container.appendChild(h2);
            
            const content = document.createElement('div');
            content.innerHTML = task.contentHtml;
            container.appendChild(content);
            
            augmentTaskUI(h2, task, true);
            
            // Add to left menu TOC
            const activeLi = document.querySelector('.md-sidebar--primary .md-nav__item--active');
            if (activeLi) {
                let tocList = activeLi.querySelector('nav.md-nav--secondary');
                if (!tocList) {
                    // Create TOC container if it doesn't exist
                    tocList = document.createElement('nav');
                    tocList.className = 'md-nav md-nav--secondary';
                    const ul = document.createElement('ul');
                    ul.className = 'md-nav__list';
                    tocList.appendChild(ul);
                    activeLi.appendChild(tocList);
                }
                
                let targetUl;
                const uls = tocList.querySelectorAll('ul.md-nav__list');
                if (uls.length > 1) {
                    targetUl = uls[uls.length - 1]; // The nested one for H2s
                } else if (uls.length === 1) {
                    const h1Li = uls[0].querySelector('li.md-nav__item');
                    if (h1Li) {
                        const nestedNav = document.createElement('nav');
                        nestedNav.className = 'md-nav';
                        targetUl = document.createElement('ul');
                        targetUl.className = 'md-nav__list';
                        nestedNav.appendChild(targetUl);
                        h1Li.appendChild(nestedNav);
                    } else {
                        targetUl = uls[0];
                    }
                } else {
                    targetUl = document.createElement('ul');
                    targetUl.className = 'md-nav__list';
                    tocList.appendChild(targetUl);
                }
                
                const li = document.createElement('li');
                li.className = 'md-nav__item';
                const a = document.createElement('a');
                a.className = 'md-nav__link';
                a.href = '#' + h2.id;
                a.textContent = h2.textContent;
                li.appendChild(a);
                targetUl.appendChild(li);
            }
        });
    }
    
    // Bookmarks page
    if (currentPath.includes('/bookmarks')) {
        renderBookmarksPage();
    }
    
    function augmentTaskUI(h2, task, isMoved = false) {
        const panel = document.createElement('div');
        panel.className = 'task-controls';
        
        const starBtn = document.createElement('button');
        starBtn.className = 'bookmark-btn ' + (task.isBookmarked ? 'active' : '');
        starBtn.innerHTML = task.isBookmarked ? '★' : '☆';
        starBtn.onclick = () => {
            task.isBookmarked = !task.isBookmarked;
            starBtn.innerHTML = task.isBookmarked ? '★' : '☆';
            starBtn.classList.toggle('active');
            saveTask(task);
        };
        
        const checkLabel = document.createElement('label');
        checkLabel.className = 'task-check';
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.checked = !!task.isCompleted;
        checkLabel.appendChild(checkbox);
        checkLabel.appendChild(document.createTextNode(' Проработано'));
        
        const applyCompletionStyle = () => {
            h2.style.textDecoration = task.isCompleted ? 'line-through' : 'none';
            h2.style.opacity = task.isCompleted ? '0.6' : '1';
        };
        applyCompletionStyle();
        
        checkbox.onchange = () => {
            task.isCompleted = checkbox.checked;
            saveTask(task);
            applyCompletionStyle();
        };
        
        const catSelect = document.createElement('select');
        catSelect.className = 'task-category-select';
        CATEGORIES.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c.id;
            opt.textContent = c.name;
            if ((task.customCategory || task.originalCategory) === c.id) opt.selected = true;
            catSelect.appendChild(opt);
        });
        catSelect.onchange = () => {
            if (catSelect.value === task.originalCategory) {
                delete task.customCategory;
            } else {
                task.customCategory = catSelect.value;
            }
            saveTask(task);
            location.reload(); 
        };
        
        panel.appendChild(starBtn);
        panel.appendChild(checkLabel);
        panel.appendChild(catSelect);
        
        // Tags panel
        const tagsContainer = document.createElement('div');
        tagsContainer.className = 'task-tags';
        
        const renderTags = () => {
            tagsContainer.innerHTML = '';
            (task.tags || []).forEach(tag => {
                const tagSpan = document.createElement('span');
                tagSpan.className = 'task-tag-badge';
                tagSpan.innerHTML = `<span>#${tag}</span>`;
                const delSpan = document.createElement('span');
                delSpan.textContent = '✖';
                delSpan.style.cursor = 'pointer';
                delSpan.onclick = () => {
                    task.tags = task.tags.filter(t => t !== tag);
                    saveTask(task);
                    renderTags();
                };
                tagSpan.appendChild(delSpan);
                tagsContainer.appendChild(tagSpan);
            });
            
            // Add tag select
            const tagSelect = document.createElement('select');
            tagSelect.className = 'task-tag-select';
            const defaultOpt = document.createElement('option');
            defaultOpt.value = '';
            defaultOpt.textContent = '+ Хэштег';
            tagSelect.appendChild(defaultOpt);
            
            AVAILABLE_TAGS.forEach(t => {
                if (!(task.tags || []).includes(t)) {
                    const opt = document.createElement('option');
                    opt.value = t;
                    opt.textContent = t;
                    tagSelect.appendChild(opt);
                }
            });
            
            tagSelect.onchange = () => {
                const val = tagSelect.value;
                if (val) {
                    task.tags = task.tags || [];
                    if (!task.tags.includes(val)) {
                        task.tags.push(val);
                        saveTask(task);
                        renderTags();
                    }
                }
            };
            
            tagsContainer.appendChild(tagSelect);
        };
        renderTags();
        panel.appendChild(tagsContainer);
        
        h2.parentNode.insertBefore(panel, h2.nextSibling);
        
        // Scripts
        const scriptsPanel = document.createElement('div');
        scriptsPanel.className = 'task-scripts';
        
        const scriptsContentPanel = document.createElement('div');
        scriptsContentPanel.className = 'task-scripts-content';
        
        const renderScripts = () => {
            scriptsPanel.innerHTML = '';
            scriptsContentPanel.innerHTML = '';
            
            (task.linkedScripts || []).forEach((script, idx) => {
                const s = document.createElement('div');
                s.className = 'script-tag ' + script.type;
                s.innerHTML = (script.type === 'main' ? '🎯 <b>Осн:</b> ' : '💡 <b>Альт:</b> ') + script.path;
                
                const del = document.createElement('span');
                del.textContent = ' ✖';
                del.style.cursor = 'pointer';
                del.onclick = () => {
                    task.linkedScripts.splice(idx, 1);
                    saveTask(task);
                    renderScripts();
                };
                s.appendChild(del);
                scriptsPanel.appendChild(s);
                
                // Render code content in a collapsible details element
                const details = document.createElement('details');
                details.className = 'script-details';
                const summary = document.createElement('summary');
                summary.textContent = `📄 ${script.type === 'main' ? 'Основной пример' : 'Альтернативное решение'}: ${script.path.split('/').pop()}`;
                details.appendChild(summary);
                
                const pre = document.createElement('pre');
                pre.className = 'script-pre';
                const codeNode = document.createElement('code');
                pre.appendChild(codeNode);
                details.appendChild(pre);
                
                // We fetch the script content
                fetch(script.path)
                    .then(r => {
                        if (!r.ok) throw new Error('Not found');
                        return r.text();
                    })
                    .then(text => {
                        codeNode.textContent = text;
                    })
                    .catch(e => {
                        codeNode.textContent = '// Ошибка загрузки скрипта. Файл не найден.\n// (Убедитесь, что он лежит в папке docs, либо сделайте symlink)';
                    });
                
                scriptsContentPanel.appendChild(details);
            });
            
            const addBtn = document.createElement('button');
            addBtn.textContent = '+ Скрипт';
            addBtn.className = 'add-script-btn';
            addBtn.onclick = () => {
                addBtn.style.display = 'none';
                
                const form = document.createElement('div');
                form.className = 'script-inline-form';
                
                const input = document.createElement('input');
                input.type = 'text';
                input.placeholder = '/python_code/script.py';
                input.className = 'script-input';
                
                const select = document.createElement('select');
                select.className = 'script-select';
                const optAlt = document.createElement('option');
                optAlt.value = 'alternative';
                optAlt.textContent = '💡 Альтернативный';
                const optMain = document.createElement('option');
                optMain.value = 'main';
                optMain.textContent = '🎯 Основной';
                select.appendChild(optAlt);
                select.appendChild(optMain);
                
                const saveBtn = document.createElement('button');
                saveBtn.textContent = 'Добавить';
                saveBtn.className = 'script-save-btn';
                saveBtn.onclick = () => {
                    const path = input.value.trim();
                    if (!path) {
                        input.focus();
                        return;
                    }
                    const type = select.value;
                    
                    task.linkedScripts = task.linkedScripts || [];
                    if (type === 'main') {
                        task.linkedScripts = task.linkedScripts.filter(s => s.type !== 'main');
                    }
                    task.linkedScripts.push({path, type});
                    saveTask(task);
                    renderScripts();
                };
                
                const cancelBtn = document.createElement('button');
                cancelBtn.textContent = 'Отмена';
                cancelBtn.className = 'script-cancel-btn';
                cancelBtn.onclick = () => {
                    renderScripts();
                };
                
                form.appendChild(input);
                form.appendChild(select);
                form.appendChild(saveBtn);
                form.appendChild(cancelBtn);
                
                scriptsPanel.appendChild(form);
                input.focus();
            };
            scriptsPanel.appendChild(addBtn);
        };
        renderScripts();
        h2.parentNode.insertBefore(scriptsPanel, panel.nextSibling);
        h2.parentNode.insertBefore(scriptsContentPanel, scriptsPanel.nextSibling);
        
        // Textarea
        let lastNode = scriptsPanel;
        if (!isMoved && !currentPath.includes('/bookmarks')) {
            let n = scriptsPanel.nextElementSibling;
            while(n && n.tagName !== 'H2') {
                lastNode = n;
                n = n.nextElementSibling;
            }
        } else {
            lastNode = h2.nextElementSibling.nextElementSibling.nextElementSibling; // div content
        }
        
        const codeArea = document.createElement('textarea');
        codeArea.className = 'bookmark-code';
        codeArea.placeholder = 'Пишите сюда примеры кода или свои заметки...';
        codeArea.value = task.codeExample || '';
        codeArea.onblur = () => {
            task.codeExample = codeArea.value;
            saveTask(task);
        };
        
        if (lastNode && lastNode.parentNode) {
            lastNode.parentNode.insertBefore(codeArea, lastNode.nextSibling);
            // Visual separator
            const sep = document.createElement('hr');
            sep.className = 'task-separator';
            lastNode.parentNode.insertBefore(sep, lastNode.nextSibling.nextSibling);
        }
    }
    
    function renderBookmarksPage() {
        const container = document.getElementById('bookmarks-container');
        if (!container) return;
        
        const allTasks = Object.values(getTasks()).filter(t => t.isBookmarked);
        container.innerHTML = '';
        
        if (allTasks.length === 0) {
            container.innerHTML = '<p>Нет закладок.</p>';
            return;
        }
        
        allTasks.forEach(task => {
            const item = document.createElement('div');
            item.className = 'bookmark-item' + (task.isCompleted ? ' completed' : '');
            
            const h2 = document.createElement('h2');
            h2.id = 'bm-' + task.id.split('#')[1];
            h2.innerHTML = `<a href="${task.originalCategory}#${task.id.split('#')[1]}">${task.title}</a>`;
            item.appendChild(h2);
            
            const content = document.createElement('div');
            content.className = 'bookmark-content';
            content.innerHTML = task.contentHtml;
            item.appendChild(content);
            
            container.appendChild(item);
            
            augmentTaskUI(h2, task, true);
        });
    }
    
    // Сворачивание оглавления (TOC) активной страницы в левом меню
    const activeLinks = document.querySelectorAll('.md-sidebar--primary .md-nav__item--active > a.md-nav__link--active');
    activeLinks.forEach(activeLink => {
        const activeLi = activeLink.closest('.md-nav__item--active');
        const tocList = activeLi ? activeLi.querySelector('nav.md-nav--secondary') : null;
        // Проверяем, что за ссылкой идет блок навигации (TOC) и мы еще не добавили стрелку
        if (tocList && !activeLink.querySelector('.custom-toc-toggle')) {
            // Создаем кастомный маркер сворачивания
            const toggleIcon = document.createElement('span');
            toggleIcon.className = 'custom-toc-toggle';
            toggleIcon.innerHTML = '▾';
            toggleIcon.style.marginLeft = 'auto';
            toggleIcon.style.transition = 'transform 0.2s';
            toggleIcon.style.fontSize = '1.2em';
            
            activeLink.style.display = 'flex';
            activeLink.style.alignItems = 'center';
            activeLink.style.cursor = 'pointer';
            activeLink.appendChild(toggleIcon);
            
            let isExpanded = true;
            activeLink.addEventListener('click', (e) => {
                // Если клик по текущей странице (чтобы не перезагружать ее)
                const href = activeLink.getAttribute('href');
                if (!href || href === '.' || href === window.location.pathname || activeLink.href === window.location.href) {
                    e.preventDefault();
                    isExpanded = !isExpanded;
                    tocList.style.display = isExpanded ? 'block' : 'none';
                    toggleIcon.style.transform = isExpanded ? 'rotate(0deg)' : 'rotate(-90deg)';
                }
            });
        }
    });
});
