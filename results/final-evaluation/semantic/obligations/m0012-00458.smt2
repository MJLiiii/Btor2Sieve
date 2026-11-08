(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 3))
(assert
 true)
(assert
 (let (($x156 (bvsge i_4 (_ bv0 3))))
(not $x156)))
(check-sat)
