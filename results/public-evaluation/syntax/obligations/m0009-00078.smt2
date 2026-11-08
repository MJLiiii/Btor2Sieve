(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_7 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x114 (bvsle s_7 (_ bv255 8))))
(not $x114)))
(check-sat)
