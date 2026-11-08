(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 3))
(assert
 true)
(assert
 (let (($x73 (bvsge i_4 (_ bv7 3))))
(not $x73)))
(check-sat)
