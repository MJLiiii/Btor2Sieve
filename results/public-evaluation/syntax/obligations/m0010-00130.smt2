(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_7 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x456 (bvsge i_7 (_ bv255 8))))
(not $x456)))
(check-sat)
