(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 32))
(assert
 true)
(assert
 (let (($x88 (bvsge i_4 (_ bv4294967295 32))))
(not $x88)))
(check-sat)
