(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_5 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x77 (bvsge s_5 (_ bv255 8))))
(not $x77)))
(check-sat)
