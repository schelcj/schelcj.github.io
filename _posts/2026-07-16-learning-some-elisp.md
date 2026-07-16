---
layout: post
title: 'learning some elisp'
date: '2026-07-16 10:39:30 -0400'
categories: ["elisp","emacs","plan.cat","finger","wip"]
comments: true
---

Been using [emacs] for awhile now but haven't really been wrint much elisp. I've had
an account on [plan.cat] but not used it much for updates to my [.plan]. Decided to
start using both more and create a function for me to update my .plan from emacs whenever
something strikes my fancy.

Since I learn best from examples I've referencing the existing [plancat.el] package. The
following retrieves my current .plan from the site and puts the contents into a new
buffer to edit. Next is to figure out how to take the contents of that buffer and send
back to [plan.cat].

{% highlight elisp %}
(defun my/plan.cat ()
  "Retrieve and edit my current plan at plan.cat."
  (interactive)
  (let* ((host "plan.cat")
      (entry (car (auth-source-search :host host)))
      (user (plist-get entry :user))
      (url (format "https://%s/~%s" host user))
      (buf (get-buffer-create host))
      (cur
       (with-current-buffer (url-retrieve-synchronously url)
           (buffer-substring-no-properties (point-min) (point-max)))))

  (with-current-buffer buf
    (erase-buffer)
    (insert
     (replace-regexp-in-string
      (rx bos (+? anything) "\n\n")
      ""
      cur))
    (goto-char (point-min))
    (text-mode))

  (switch-to-buffer-other-window buf)))
{% endhighlight %}

[emacs]: https://www.gnu.org/software/emacs/
[plan.cat]: https://plan.cat
[.plan]: https://plan.cat/~schelcj
[plancat.el]: https://codeberg.org/acdw/plancat.el/src/branch/main/plancat.el
