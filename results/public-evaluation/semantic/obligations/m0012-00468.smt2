(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 3))
(assert
 true)
(assert
 (let (($x27 (bvsge i_4 (_ bv7 3))))
(not $x27)))
(check-sat)
