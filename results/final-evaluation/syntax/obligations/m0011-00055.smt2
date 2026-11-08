(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_2 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x303 (bvsge i_2 (_ bv0 4))))
(not $x303)))
(check-sat)
